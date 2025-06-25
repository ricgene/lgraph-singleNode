"""
Cloud Function for processing incoming emails with Firebase Authentication and LangGraph integration.
"""
import os
import json
import logging
import functions_framework
from flask import Request
from typing import Dict, Any
import google.cloud.logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth, firestore
from langgraph_sdk import get_sync_client
import requests

# Load environment variables
load_dotenv()

# Set up Cloud Logging
try:
    client = google.cloud.logging.Client()
    client.setup_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Helper function to create task-specific keys
def create_task_key(user_email, task_title, timestamp=None):
    if not timestamp:
        from datetime import datetime
        timestamp = datetime.now().isoformat()
    return f"taskAgent1_{user_email}_{task_title}_{timestamp}"

# Helper function to create task ID
def create_task_id(user_email, task_title, timestamp=None):
    if not timestamp:
        from datetime import datetime
        timestamp = datetime.now().isoformat()
    return f"{user_email}_{task_title}_{timestamp}"

# Helper function to find existing task
def find_existing_task(user_email, task_title):
    try:
        task_agent_ref = db.collection('taskAgent1')
        docs = task_agent_ref.stream()
        
        for doc in docs:
            data = doc.to_dict()
            if (data.get('currentTask') and 
                data['currentTask'].get('userEmail') == user_email and 
                data['currentTask'].get('taskTitle') == task_title and
                data['currentTask'].get('status') != 'completed'):
                return {
                    'taskKey': doc.id,
                    'taskData': data['currentTask']
                }
        
        return None
    except Exception as error:
        logger.error(f'Error finding existing task: {error}')
        return None

# Helper function to create new task
def create_new_task(user_email, task_title):
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    task_key = create_task_key(user_email, task_title, timestamp)
    task_id = create_task_id(user_email, task_title, timestamp)
    
    task_agent_state = {
        'agentStateKey': task_key,
        'currentTask': {
            'taskId': task_id,
            'taskTitle': task_title,
            'userEmail': user_email,
            'createdAt': timestamp,
            'lastUpdated': timestamp,
            'status': 'active',
            'emailLock': None,
            'lastMsgSent': None,
            'conversationHistory': []
        },
        'createdAt': timestamp,
        'lastUpdated': timestamp
    }
    
    db.collection('taskAgent1').document(task_key).set(task_agent_state)
    logger.info(f'✅ Created new task: {task_id} with key: {task_key}')
    
    return {
        'taskKey': task_key,
        'taskData': task_agent_state['currentTask']
    }

# Distributed locking functions
def acquire_email_lock(customer_email, task_title):
    # First, try to find existing task
    existing_task = find_existing_task(customer_email, task_title)
    task_key = None
    task_agent_state = None
    
    if existing_task:
        # Use existing task
        task_key = existing_task['taskKey']
        doc_ref = db.collection('taskAgent1').document(task_key)
        doc = doc_ref.get()
        task_agent_state = doc.to_dict()
        logger.info(f'📋 Found existing task: {existing_task["taskData"]["taskId"]}')
    else:
        # Create new task
        new_task = create_new_task(customer_email, task_title)
        task_key = new_task['taskKey']
        doc_ref = db.collection('taskAgent1').document(task_key)
        doc = doc_ref.get()
        task_agent_state = doc.to_dict()
        logger.info(f'🆕 Created new task: {new_task["taskData"]["taskId"]}')
    
    # Ensure emailLock field exists for existing tasks
    if 'emailLock' not in task_agent_state['currentTask']:
        task_agent_state['currentTask']['emailLock'] = None
    
    # Wait random amount of time (0-1 second)
    import random
    import time
    wait_time = random.random() * 1000
    logger.info(f'⏳ Waiting {wait_time:.0f}ms before attempting lock acquisition')
    time.sleep(wait_time / 1000)
    
    # Get last 4 digits of high-resolution timestamp
    lock_timestamp = int(time.time() * 1000)
    last_4_digits = str(lock_timestamp)[-4:]
    logger.info(f'🔒 Attempting to acquire lock with digits: {last_4_digits} (timestamp: {lock_timestamp})')
    
    # Check if lock is already held
    if (task_agent_state['currentTask']['emailLock'] and 
        (time.time() * 1000 - task_agent_state['currentTask']['emailLock']['timestamp']) < 30000):
        logger.info(f'🚫 Email lock already held for {customer_email} - {task_title}')
        return False
    
    # Acquire lock
    from datetime import datetime
    task_agent_state['currentTask']['emailLock'] = {
        'timestamp': datetime.now().isoformat(),
        'lockId': last_4_digits,
        'taskTitle': task_title
    }
    task_agent_state['currentTask']['lastUpdated'] = datetime.now().isoformat()
    
    db.collection('taskAgent1').document(task_key).set(task_agent_state)
    logger.info(f'🔒 Successfully acquired email lock for {customer_email} - {task_title} (lock: {last_4_digits})')
    return last_4_digits

def clear_email_lock(customer_email, task_title):
    # Find existing task
    existing_task = find_existing_task(customer_email, task_title)
    if not existing_task:
        logger.info(f'⚠️ No task found to clear lock for {customer_email} - {task_title}')
        return
    
    doc_ref = db.collection('taskAgent1').document(existing_task['taskKey'])
    doc = doc_ref.get()
    task_agent_state = doc.to_dict()
    
    if task_agent_state['currentTask']:
        task_agent_state['currentTask']['emailLock'] = None
        from datetime import datetime
        task_agent_state['currentTask']['lastUpdated'] = datetime.now().isoformat()
        db.collection('taskAgent1').document(existing_task['taskKey']).set(task_agent_state)
        logger.info(f'🔓 Cleared email lock for {customer_email} - {task_title}')

# LangGraph processing function
def process_user_response(user_email, user_response, conversation_state):
    try:
        # Import the langgraph_sdk client
        from langgraph_sdk import get_sync_client
        
        # Get LangGraph deployment URL and API key from environment
        langgraph_deployment_url = os.getenv("LANGGRAPH_DEPLOYMENT_URL")
        langgraph_api_key = os.getenv("LANGGRAPH_API_KEY")
        
        if not langgraph_deployment_url:
            logger.error("❌ LANGGRAPH_DEPLOYMENT_URL not found in environment variables")
            return None
        
        if not langgraph_api_key:
            logger.error("❌ LANGGRAPH_API_KEY not found in environment variables")
            return None
        
        # Initialize the langgraph client using the deployment URL
        client = get_sync_client(
            url=langgraph_deployment_url,
            api_key=langgraph_api_key
        )
        
        # Create input data matching the oneNodeRemMem expected format
        input_data = {
            "user_input": user_response,
            "previous_state": {
                "conversation_history": conversation_state.get("conversation_history", ""),
                "is_complete": conversation_state.get("is_complete", False),
                "user_email": user_email
            }
        }
        
        logger.info(f"📡 Calling deployed LangGraph service: {langgraph_deployment_url}")
        logger.info(f"📤 Sending input data: {json.dumps(input_data, indent=2)}")
        
        # Stream the graph execution
        graph_output = []
        for chunk in client.runs.stream(
            None,  # Threadless run
            "moBettah",  # Name of your deployed assistant
            input=input_data,
            stream_mode="updates",
        ):
            logger.info(f"Receiving new event of type: {chunk.event}...")
            logger.info(f"Chunk data: {chunk.data}")
            graph_output.append(chunk.data)
        
        logger.info(f"✅ LangGraph processing successful for {user_email}")
        
        # Extract the response from the graph output
        # The oneNodeRemMem returns a specific format with question, conversation_history, etc.
        if graph_output:
            # Look for the final response in the graph output
            final_response = None
            for chunk in reversed(graph_output):
                if isinstance(chunk, dict) and "question" in chunk:
                    final_response = chunk
                    break
            
            if final_response:
                response_data = {
                    "question": final_response.get("question", ""),
                    "conversation_history": final_response.get("conversation_history", ""),
                    "is_complete": final_response.get("is_complete", False),
                    "completion_state": final_response.get("completion_state", "OTHER"),
                    "user_email": final_response.get("user_email", user_email)
                }
            else:
                # Fallback if we can't find the expected response format
                response_data = {
                    "question": "Processing completed",
                    "conversation_history": conversation_state.get("conversation_history", ""),
                    "is_complete": False,
                    "completion_state": "OTHER",
                    "user_email": user_email
                }
        else:
            # No output received
            response_data = {
                "question": "No response received from LangGraph",
                "conversation_history": conversation_state.get("conversation_history", ""),
                "is_complete": False,
                "completion_state": "OTHER",
                "user_email": user_email
            }
        
        logger.info(f"📤 Returning response data: {json.dumps(response_data, indent=2)}")
        return response_data
        
    except Exception as error:
        logger.error(f"❌ Error processing with LangGraph for {user_email}: {error}")
        logger.exception("Full traceback:")
        return None

# Firebase Authentication middleware
def verify_auth_token(request):
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise Exception('No valid authorization header')

        token = auth_header.split('Bearer ')[1]
        if not token:
            raise Exception('No token provided')

        # Use Firebase Admin SDK to verify the token
        decoded_token = auth.verify_id_token(token)
        
        # Handle tokens that might not have email (like custom tokens)
        user_email = decoded_token.get('email')
        if not user_email:
            # For custom tokens, we'll use the email from the request body
            request_json = request.get_json(silent=True)
            if request_json:
                user_email = request_json.get('userEmail')
            else:
                user_email = "test@prizmpoc.com"  # Default fallback
        
        return {'uid': decoded_token.get('uid', 'test-user'), 'email': user_email}
    except Exception as error:
        logger.error(f'Authentication error: {error}')
        raise error

@functions_framework.http
def process_email(request: Request):
    """Cloud Function entry point for processing emails with LangGraph."""
    
    # Set CORS headers
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return ('', 204, response_headers)
    
    try:
        # Verify Firebase authentication
        auth_user = verify_auth_token(request)
        if not auth_user:
            logger.error('❌ Authentication failed: No valid token provided')
            return (json.dumps({
                'success': False,
                'message': 'Authentication required'
            }), 401, response_headers)
        
        # Parse request body
        request_json = request.get_json(silent=True)
        if not request_json:
            return (json.dumps({
                'success': False,
                'message': 'No JSON data in request'
            }), 400, response_headers)
        
        user_email = request_json.get('userEmail')
        user_response = request_json.get('userResponse')
        task_title = request_json.get('taskTitle', 'Prizm Task Question')
        
        if not user_email or not user_response:
            return (json.dumps({
                'success': False,
                'message': 'Missing required fields: userEmail, userResponse'
            }), 400, response_headers)
        
        # Verify that the authenticated user matches the userEmail in the request
        if auth_user['email'] != user_email:
            logger.error(f'❌ User email mismatch: authenticated={auth_user["email"]}, request={user_email}')
            return (json.dumps({
                'success': False,
                'message': 'User email mismatch'
            }), 403, response_headers)
        
        logger.info(f'📧 Processing email from: {user_email}')
        logger.info(f'📝 User response: {user_response}')
        logger.info(f'📋 Task title: {task_title}')
        
        # Try to acquire email lock to prevent duplicate processing
        lock_acquired = acquire_email_lock(user_email, task_title)
        if not lock_acquired:
            logger.info(f'🚫 Failed to acquire lock for {user_email} - {task_title}. Another responder is processing this email.')
            return (json.dumps({
                'success': False,
                'message': 'Email already being processed by another instance'
            }), 200, response_headers)
        
        logger.info(f'✅ Successfully acquired lock ({lock_acquired}) for {user_email} - {task_title}')
        
        # Get existing task conversation using task discovery
        existing_task = find_existing_task(user_email, task_title)
        task_data = None
        
        if existing_task:
            task_data = existing_task['taskData']
            logger.info(f'📋 Found existing task: {existing_task["taskData"]["taskId"]}')
        else:
            logger.info(f'🆕 No existing task found, will create new one when needed')
        
        # Create conversation history for LangGraph
        conversation_history = ""
        if task_data and task_data.get('conversationHistory'):
            conversation_history = "\n\n".join([
                f"User: {turn['userMessage']}\nAgent: {turn['agentResponse']}"
                for turn in task_data['conversationHistory']
            ])
        
        # Create temporary conversation state for LangGraph processing
        temp_conversation_state = {
            'conversation_history': conversation_history,
            'is_complete': False,
            'user_email': user_email
        }
        
        # Process the user's response through LangGraph
        result = process_user_response(user_email, user_response, temp_conversation_state)
        
        if not result:
            logger.info(f'❌ LangGraph processing failed for {user_email}')
            clear_email_lock(user_email, task_title)
            return (json.dumps({
                'success': False,
                'message': 'Failed to process with LangGraph'
            }), 500, response_headers)
        
        # For now, just return success without email sending
        # You can add email sending logic here later
        clear_email_lock(user_email, task_title)
        
        return (json.dumps({
            'success': True,
            'message': 'Email processed successfully with LangGraph',
            'result': result
        }), 200, response_headers)
        
    except Exception as error:
        logger.error(f'❌ Cloud function error: {error}')
        return (json.dumps({
            'success': False,
            'message': 'Internal server error',
            'error': str(error)
        }), 500, response_headers) 