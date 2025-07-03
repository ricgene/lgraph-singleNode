"""
Telegram Bot Google Cloud Function (Using Unified Messaging)
Handles incoming Telegram webhook updates using the unified messaging abstraction
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Optional

import functions_framework
from flask import Request
import firebase_admin
from firebase_admin import credentials, firestore

# Add messaging module to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

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
    message_manager,
    message_handler
)

# Initialize Telegram provider
telegram_provider = None

def _initialize_telegram_provider():
    """Initialize Telegram provider if not already done"""
    global telegram_provider
    if not telegram_provider:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        if bot_token:
            telegram_provider = TelegramProvider({'bot_token': bot_token})
            message_manager.register_provider(telegram_provider, is_default=True)
            logger.info("Telegram provider initialized and registered")
        else:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
    return telegram_provider

def store_telegram_mapping(username: str, chat_id: str, user_data: dict = None):
    """Store mapping between Telegram username and chat_id in Firestore"""
    try:
        clean_username = username.lower()
        
        mapping_data = {
            'username': clean_username,
            'chat_id': str(chat_id),
            'last_seen': datetime.now().isoformat(),
            'user_data': user_data or {}
        }
        
        doc_ref = db.collection('telegram_users').document(clean_username)
        doc_ref.set(mapping_data, merge=True)
        
        logger.info(f"Stored Telegram mapping: {clean_username} -> {chat_id}")
        
    except Exception as e:
        logger.error(f"Error storing Telegram mapping: {str(e)}")

def check_and_initiate_pending_tasks(incoming_message):
    """Check for pending tasks for this user and initiate them"""
    try:
        username = incoming_message.username
        if not username:
            return
        
        # Look for pending tasks for this username
        tasks_ref = db.collection('tasks')
        query = tasks_ref.where('telegram_username', '==', f'@{username.lower()}').where('waiting_for_user_init', '==', True)
        
        pending_tasks = query.stream()
        
        for task_doc in pending_tasks:
            task_data = task_doc.to_dict()
            task_id = task_data.get('task_id')
            
            logger.info(f"Found pending task {task_id} for user @{username}")
            
            # Send the initial greeting for this task
            greeting = (f"Hello {task_data.get('customer_name', username)}! "
                       f"I'm Helen, your AI assistant from Prizm Real Estate Concierge Service. "
                       f"I'm here to help you with your {task_data.get('task_title', 'task')} project. "
                       f"Let's get started with a few questions to better understand your needs.")
            
            # Send via Telegram
            from messaging.base import OutgoingMessage
            outgoing_message = OutgoingMessage(
                text=greeting,
                chat_id=incoming_message.chat_id
            )
            
            result = message_manager.send_message(outgoing_message, MessageProvider.TELEGRAM)
            
            if result.success:
                # Update task to mark as initiated
                task_doc.reference.update({
                    'waiting_for_user_init': False,
                    'conversation_initiated_at': datetime.now().isoformat(),
                    'conversation_state.turn_count': 1,
                    'conversation_state.last_response': greeting,
                    'conversation_state.conversation_history': f"Agent: {greeting}",
                    'conversation_state.waiting_for_telegram_init': False,
                    'actual_chat_id': incoming_message.chat_id
                })
                
                logger.info(f"Successfully initiated task {task_id} for @{username}")
            else:
                logger.error(f"Failed to send initial message for task {task_id}: {result.error}")
        
    except Exception as e:
        logger.error(f"Error checking pending tasks: {str(e)}")

@functions_framework.http
def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates using unified messaging"""
    
    # Only accept POST requests
    if request.method != 'POST':
        return {"error": "Only POST requests allowed"}, 405
    
    try:
        # Initialize Telegram provider
        provider = _initialize_telegram_provider()
        if not provider:
            return {"error": "Telegram provider not configured"}, 500
        
        # Get JSON data from request
        raw_data = request.get_json(silent=True)
        
        if not raw_data:
            logger.warning("No JSON data received")
            return {"error": "No data received"}, 400
        
        logger.info(f"Received Telegram webhook data")
        
        # Parse incoming message using unified system
        incoming_message = message_manager.parse_webhook(raw_data, MessageProvider.TELEGRAM)
        
        if not incoming_message:
            logger.info("No valid message found in webhook data")
            return {"status": "ignored", "reason": "no valid message"}, 200
        
        logger.info(f"Processing message from user {incoming_message.user_id}: {incoming_message.text}")
        
        # Store username/chat_id mapping for future use
        if incoming_message.username:
            store_telegram_mapping(incoming_message.username, incoming_message.chat_id, {
                'user_id': incoming_message.user_id,
                'first_name': incoming_message.first_name,
                'last_name': incoming_message.last_name
            })
        
        # Check for pending tasks for this user
        check_and_initiate_pending_tasks(incoming_message)
        
        # Process message using unified handler
        result = message_handler.process_message(incoming_message)
        
        if result.success:
            logger.info("Message processed and response sent successfully")
            return {"status": "success", "message_sent": True}, 200
        else:
            logger.error(f"Failed to process message: {result.error}")
            return {"error": "Failed to process message", "details": result.error}, 500
            
    except Exception as e:
        logger.error(f"Error handling Telegram webhook: {str(e)}")
        return {"error": "Internal server error"}, 500

@functions_framework.http
def telegram_setup(request: Request):
    """Setup Telegram webhook using unified messaging system"""
    
    if request.method != 'POST':
        return {"error": "Only POST requests allowed"}, 405
    
    try:
        # Initialize Telegram provider
        provider = _initialize_telegram_provider()
        if not provider:
            return {"error": "Telegram provider not configured"}, 500
        
        data = request.get_json(silent=True) or {}
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            return {"error": "webhook_url required"}, 400
        
        # Use provider's webhook management
        result = provider.set_webhook(webhook_url)
        
        return result, 200 if result.get('ok') else 500
        
    except Exception as e:
        logger.error(f"Error setting up webhook: {str(e)}")
        return {"error": "Internal server error"}, 500