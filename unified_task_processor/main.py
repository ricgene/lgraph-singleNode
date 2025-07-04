"""
Unified Task Processor Cloud Function
Routes tasks to appropriate messaging channel based on phone number format
- Phone starts with [0-9] → SMS (Twilio/MessageCentral)
- Phone doesn't start with [0-9] → Telegram handle
"""

import os
import sys
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional

import functions_framework
from flask import Request
import firebase_admin
from firebase_admin import credentials, firestore
from langgraph_sdk import get_sync_client

# Add messaging module to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Import unified messaging system
from messaging import (
    MessageProvider,
    TelegramProvider,
    TwilioProvider,
    MessageCentralProvider,
    OutgoingMessage,
    message_manager,
    message_handler
)

# Initialize messaging providers
def initialize_providers():
    """Initialize all messaging providers"""
    providers_initialized = []
    
    try:
        logger.info("Starting provider initialization...")
        
        # Initialize Telegram provider
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        logger.info(f"Telegram token available: {bool(telegram_token)}")
        
        if telegram_token:
            try:
                telegram_provider = TelegramProvider({'bot_token': telegram_token})
                message_manager.register_provider(telegram_provider)
                providers_initialized.append('Telegram')
                logger.info("✅ Telegram provider initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Telegram provider: {str(e)}")
        else:
            logger.warning("⚠️ TELEGRAM_BOT_TOKEN not found")
        
        # Initialize Twilio provider
        twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
        logger.info(f"Twilio credentials available: {bool(twilio_sid and twilio_token)}")
        
        if twilio_sid and twilio_token:
            try:
                twilio_provider = TwilioProvider({
                    'account_sid': twilio_sid,
                    'auth_token': twilio_token,
                    'phone_number': os.getenv('TWILIO_PHONE_NUMBER')
                })
                message_manager.register_provider(twilio_provider)
                providers_initialized.append('Twilio')
                logger.info("✅ Twilio provider initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio provider: {str(e)}")
        
        # Initialize MessageCentral provider
        mc_customer_id = os.getenv('MC_CUSTOMER_ID')
        logger.info(f"MessageCentral credentials available: {bool(mc_customer_id)}")
        
        if mc_customer_id:
            try:
                mc_provider = MessageCentralProvider({
                    'customer_id': mc_customer_id,
                    'password': os.getenv('MC_PASSWORD'),
                    'password_base64': os.getenv('MC_PASSWORD_BASE64')
                })
                message_manager.register_provider(mc_provider)
                providers_initialized.append('MessageCentral')
                logger.info("✅ MessageCentral provider initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize MessageCentral provider: {str(e)}")
        
        logger.info(f"🎉 Provider initialization complete. Initialized: {providers_initialized}")
        return providers_initialized
        
    except Exception as e:
        logger.error(f"❌ Critical error during provider initialization: {str(e)}")
        return []

# Initialize providers on startup
logger.info("🚀 Starting unified task processor...")
try:
    initialized_providers = initialize_providers()
    logger.info(f"📊 Available providers: {[p.value for p in message_manager.providers.keys()]}")
except Exception as e:
    logger.error(f"❌ Failed to initialize providers: {str(e)}")

def store_telegram_user_mapping(username: str, chat_id: str, user_data: dict = None):
    """Store mapping between Telegram username and chat_id in Firestore"""
    try:
        # Clean username (remove @ if present)
        clean_username = username.lstrip('@').lower()
        
        mapping_data = {
            'username': clean_username,
            'chat_id': str(chat_id),
            'last_seen': datetime.now().isoformat(),
            'user_data': user_data or {}
        }
        
        doc_ref = db.collection('telegram_users').document(clean_username)
        doc_ref.set(mapping_data, merge=True)
        
        logger.info(f"Stored Telegram mapping: {clean_username} -> {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing Telegram user mapping: {str(e)}")
        return False

def lookup_telegram_chat_id(username: str) -> Optional[str]:
    """Look up chat_id for a Telegram username"""
    try:
        # Clean username (remove @ if present)
        clean_username = username.lstrip('@').lower()
        
        doc_ref = db.collection('telegram_users').document(clean_username)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            chat_id = data.get('chat_id')
            logger.info(f"Found Telegram mapping: {clean_username} -> {chat_id}")
            return chat_id
        else:
            logger.warning(f"No Telegram mapping found for username: {clean_username}")
            return None
            
    except Exception as e:
        logger.error(f"Error looking up Telegram chat_id: {str(e)}")
        return None

def determine_messaging_channel(phone_number: str) -> tuple[MessageProvider, str]:
    """
    Determine messaging channel based on phone number format
    Returns: (provider_type, contact_identifier)
    """
    if not phone_number:
        raise ValueError("Phone number is required")
    
    # Check if phone number starts with digit (traditional phone)
    if re.match(r'^[0-9]', phone_number.strip()):
        # Traditional phone number - route to SMS
        # Prefer MessageCentral, fallback to Twilio
        if message_manager.get_provider(MessageProvider.MESSAGECENTRAL):
            return MessageProvider.MESSAGECENTRAL, phone_number
        elif message_manager.get_provider(MessageProvider.TWILIO):
            return MessageProvider.TWILIO, phone_number
        else:
            raise ValueError("No SMS provider available")
    else:
        # Non-numeric "phone" number - treat as Telegram handle
        if message_manager.get_provider(MessageProvider.TELEGRAM):
            # For Telegram, we need to convert handle to chat_id
            # For now, we'll store the handle and let the conversation flow handle it
            return MessageProvider.TELEGRAM, phone_number
        else:
            raise ValueError("Telegram provider not available")

def create_task_record(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a task record in Firestore"""
    try:
        # Extract key fields - handle both front-end and email formats
        customer_name = task_data.get('Customer Name', task_data.get('customerName', ''))
        customer_email = task_data.get('custemail', '')
        phone_number = (task_data.get('phone_number') or 
                       task_data.get('phone') or 
                       task_data.get('Phone', ''))
        task_title = task_data.get('Task', 'General Task')
        description = task_data.get('description', '')
        
        # Create unique task ID
        timestamp = datetime.now().isoformat()
        task_id = f"{customer_email}_{task_title}_{timestamp}".replace(' ', '_').replace('@', '_at_')
        
        # Determine messaging channel
        provider_type, contact_id = determine_messaging_channel(phone_number)
        
        # Create task record
        task_record = {
            'task_id': task_id,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'phone_number': phone_number,
            'contact_identifier': contact_id,
            'messaging_provider': provider_type.value,
            'task_title': task_title,
            'description': description,
            'category': task_data.get('Category', 'General'),
            'budget': task_data.get('Task Budget', 0),
            'address': task_data.get('FullAddress', task_data.get('Full Address', '')),
            'state': task_data.get('State', ''),
            'due_date': task_data.get('DueDate', ''),
            'posted_date': task_data.get('Posted', ''),
            'vendors': task_data.get('vendors', ''),
            'created_at': timestamp,
            'conversation_state': {
                'turn_count': 0,
                'is_complete': False,
                'conversation_history': '',
                'last_response': ''
            },
            'raw_task_data': task_data
        }
        
        # Store in Firestore
        doc_ref = db.collection('tasks').document(task_id)
        doc_ref.set(task_record)
        
        logger.info(f"Created task record {task_id} for {provider_type.value} channel")
        return task_record
        
    except Exception as e:
        logger.error(f"Error creating task record: {str(e)}")
        raise

def initiate_conversation(task_record: Dict[str, Any]) -> Dict[str, Any]:
    """Initiate conversation with customer via appropriate messaging channel"""
    try:
        provider_type = MessageProvider(task_record['messaging_provider'])
        contact_id = task_record['contact_identifier']
        
        # Create initial greeting message
        greeting = (f"Hello {task_record['customer_name']}! "
                   f"I'm Helen, your AI assistant from Prizm Real Estate Concierge Service. "
                   f"I'm here to help you with your {task_record['task_title']} project. "
                   f"Let's get started with a few questions to better understand your needs.")
        
        # Send initial message
        # For Telegram handles starting with @, lookup the chat_id
        if provider_type == MessageProvider.TELEGRAM and contact_id.startswith('@'):
            # Look up the chat_id for this username
            actual_chat_id = lookup_telegram_chat_id(contact_id)
            
            if not actual_chat_id:
                # No mapping found - store task but can't send message yet
                logger.warning(f"No chat_id found for Telegram username: {contact_id}")
                greeting += f"\n\nNote: To receive messages, please send '/start' to @Aloha116bot on Telegram to establish the connection."
                
                # Update task record to indicate waiting for user to message bot
                task_record['conversation_state']['waiting_for_telegram_init'] = True
                doc_ref = db.collection('tasks').document(task_record['task_id'])
                doc_ref.update({
                    'conversation_state': task_record['conversation_state'],
                    'telegram_username': contact_id,
                    'waiting_for_user_init': True
                })
                
                return {
                    'success': True,
                    'task_id': task_record['task_id'],
                    'provider': provider_type.value,
                    'contact_id': contact_id,
                    'message_sent': False,
                    'note': f"Task created. User needs to message @Aloha116bot to start conversation."
                }
        else:
            actual_chat_id = contact_id
        
        outgoing_message = OutgoingMessage(
            text=greeting,
            chat_id=actual_chat_id
        )
        
        result = message_manager.send_message(outgoing_message, provider_type)
        
        if result.success:
            # Update task record with conversation start
            task_record['conversation_state']['turn_count'] = 1
            task_record['conversation_state']['last_response'] = greeting
            task_record['conversation_state']['conversation_history'] = f"Agent: {greeting}"
            
            # Update Firestore
            doc_ref = db.collection('tasks').document(task_record['task_id'])
            doc_ref.update({
                'conversation_state': task_record['conversation_state'],
                'conversation_initiated_at': datetime.now().isoformat()
            })
            
            logger.info(f"Conversation initiated for task {task_record['task_id']} via {provider_type.value}")
            return {
                'success': True,
                'task_id': task_record['task_id'],
                'provider': provider_type.value,
                'contact_id': contact_id,
                'message_sent': True
            }
        else:
            logger.error(f"Failed to send initial message: {result.error}")
            return {
                'success': False,
                'task_id': task_record['task_id'],
                'error': result.error
            }
            
    except Exception as e:
        logger.error(f"Error initiating conversation: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@functions_framework.http
def process_task(request: Request):
    """
    Process incoming task from front-end and initiate conversation
    Supports both legacy email format and new unified messaging
    """
    
    if request.method != 'POST':
        return {"error": "Only POST requests allowed"}, 405
    
    try:
        # Get task data from request
        task_data = request.get_json(silent=True)
        
        if not task_data:
            return {"error": "No JSON data provided"}, 400
        
        logger.info(f"Received task data: {json.dumps(task_data, indent=2)}")
        
        # Validate required fields - handle both formats
        customer_email = task_data.get('custemail', '')
        if not customer_email:
            return {"error": "Missing required field: custemail"}, 400
        
        # Check for phone number in various possible fields
        phone_number = (task_data.get('phone_number') or 
                       task_data.get('phone') or 
                       task_data.get('Phone') or 
                       task_data.get('phoneNumber'))
        
        if not phone_number:
            return {"error": "Phone number/contact is required for messaging"}, 400
        
        task_data['phone_number'] = phone_number  # Normalize field name
        
        # Create task record
        task_record = create_task_record(task_data)
        
        # Initiate conversation
        conversation_result = initiate_conversation(task_record)
        
        if conversation_result['success']:
            return {
                "status": "success",
                "message": "Task created and conversation initiated",
                "task_id": conversation_result['task_id'],
                "messaging_provider": conversation_result['provider'],
                "contact_id": conversation_result['contact_id']
            }, 200
        else:
            return {
                "status": "error",
                "message": "Task created but conversation initiation failed",
                "task_id": task_record['task_id'],
                "error": conversation_result.get('error')
            }, 500
            
    except Exception as e:
        logger.error(f"Error processing task: {str(e)}")
        return {"error": "Internal server error", "details": str(e)}, 500

@functions_framework.http  
def get_task_status(request: Request):
    """Get the status of a task and its conversation"""
    
    if request.method != 'GET':
        return {"error": "Only GET requests allowed"}, 405
    
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return {"error": "task_id parameter required"}, 400
        
        # Get task from Firestore
        doc_ref = db.collection('tasks').document(task_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return {"error": "Task not found"}, 404
        
        task_data = doc.to_dict()
        
        return {
            "task_id": task_id,
            "customer_name": task_data.get('customer_name'),
            "task_title": task_data.get('task_title'),
            "messaging_provider": task_data.get('messaging_provider'),
            "conversation_state": task_data.get('conversation_state', {}),
            "created_at": task_data.get('created_at'),
            "conversation_initiated_at": task_data.get('conversation_initiated_at')
        }, 200
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return {"error": "Internal server error"}, 500