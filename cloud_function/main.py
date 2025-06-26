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
import base64

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

@functions_framework.cloud_event
def process_email_pubsub(cloud_event):
    """Cloud Function entry point for processing emails via Pub/Sub trigger."""
    
    try:
        logger.info(f"📨 Received cloud event: {json.dumps(cloud_event.data, indent=2)}")
        
        # Check if we have the expected message structure
        if "message" not in cloud_event.data:
            logger.error("❌ No 'message' field in cloud event data")
            return
        
        if "data" not in cloud_event.data["message"]:
            logger.error("❌ No 'data' field in message")
            return
        
        # Decode the Pub/Sub message
        try:
            pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
            logger.info(f"📨 Decoded Pub/Sub message: {pubsub_message}")
            message_data = json.loads(pubsub_message)
        except Exception as decode_error:
            logger.error(f"❌ Error decoding message: {decode_error}")
            logger.error(f"📨 Raw message data: {cloud_event.data['message']['data']}")
            return
        
        # Extract data from the message
        user_email = message_data.get('userEmail')
        user_response = message_data.get('userResponse')
        task_title = message_data.get('taskTitle', 'Prizm Task Question')
        email_uid = message_data.get('emailUid', 'unknown')
        timestamp = message_data.get('timestamp')
        
        if not user_email or not user_response:
            logger.error(f'❌ Missing required fields in Pub/Sub message: userEmail={user_email}, userResponse={user_response}')
            return
        
        # Special handling for foilboi@gmail.com - parse structured task data
        if user_email == 'foilboi@gmail.com':
            logger.info(f'🎯 Processing structured task data from foilboi@gmail.com')
            
            # Parse the structured email body
            task_data = parse_foilboi_email_body(user_response)
            if not task_data:
                logger.error(f'❌ Failed to parse structured task data from foilboi@gmail.com')
                return
            
            logger.info(f'📋 Parsed task data: {json.dumps(task_data, indent=2)}')
            
            # Extract customer email and task information
            customer_email = task_data.get('custemail', '').strip()
            customer_name = task_data.get('CustomerName', '').strip()
            task_number = task_data.get('Task', '').strip()
            task_description = task_data.get('description', '').strip()
            due_date = task_data.get('DueDate', '').strip()
            category = task_data.get('Category', '').strip()
            state = task_data.get('State', '').strip()
            vendors = task_data.get('vendors', '').strip()
            
            # Create a more descriptive task title
            task_title = f"Task {task_number} - {category} - {customer_name}"
            
            # Create the initial user response for LangGraph
            initial_response = f"""
Task Request Details:
- Customer: {customer_name} ({customer_email})
- Task Number: {task_number}
- Category: {category}
- Description: {task_description}
- Due Date: {due_date}
- State: {state}
- Vendors: {vendors}

Please help me process this task request.
"""
            
            # For the first call, we don't need to check for existing tasks
            # Just create a new task and start the workflow
            new_task = create_new_task(customer_email, task_title)
            task_data_firestore = new_task['taskData']
            
            # Store the original structured data in the task
            task_data_firestore['originalTaskData'] = task_data
            task_data_firestore['taskNumber'] = task_number
            task_data_firestore['customerName'] = customer_name
            task_data_firestore['category'] = category
            task_data_firestore['dueDate'] = due_date
            task_data_firestore['state'] = state
            task_data_firestore['vendors'] = vendors
            
            # Initialize conversation state for LangGraph
            conversation_state = {
                'conversation_history': '',
                'is_complete': False,
                'user_email': customer_email  # Use customer email for LangGraph
            }
            
            # Use the customer email for processing
            processing_email = customer_email
            user_response_for_langgraph = initial_response
            
        else:
            # For subsequent calls, use the existing workflow
            logger.info(f'📧 Processing email from: {user_email}')
            processing_email = user_email
            user_response_for_langgraph = user_response
            
            # Try to acquire email lock to prevent duplicate processing
            lock_acquired = acquire_email_lock(user_email, task_title)
            if not lock_acquired:
                logger.info(f'🚫 Failed to acquire lock for {user_email} - {task_title}. Another responder is processing this email.')
                return
            
            logger.info(f'✅ Successfully acquired lock for {user_email} - {task_title}')
            
            # Get existing task conversation using task discovery
            existing_task = find_existing_task(user_email, task_title)
            task_data_firestore = None
            
            if existing_task:
                task_data_firestore = existing_task['taskData']
                logger.info(f'📋 Found existing task: {existing_task["taskData"]["taskId"]}')
            else:
                logger.info(f'🆕 No existing task found, will create new one when needed')
                new_task = create_new_task(user_email, task_title)
                task_data_firestore = new_task['taskData']
            
            # Create conversation history for LangGraph
            conversation_history = ""
            if task_data_firestore and task_data_firestore.get('conversationHistory'):
                conversation_history = "\n\n".join([
                    f"User: {turn['userMessage']}\nAgent: {turn['agentResponse']}"
                    for turn in task_data_firestore['conversationHistory']
                ])
            
            # Create conversation state for LangGraph processing
            conversation_state = {
                'conversation_history': conversation_history,
                'is_complete': False,
                'user_email': user_email
            }
        
        logger.info(f'📝 Processing response for: {processing_email}')
        logger.info(f'📋 Task title: {task_title}')
        
        # Process the user's response through LangGraph
        result = process_user_response(processing_email, user_response_for_langgraph, conversation_state)
        
        if not result:
            logger.error(f'❌ LangGraph processing failed for {processing_email}')
            if user_email != 'foilboi@gmail.com':
                clear_email_lock(user_email, task_title)
            return
        
        # Update task with conversation history
        if task_data_firestore:
            # Add the new conversation turn
            if 'conversationHistory' not in task_data_firestore:
                task_data_firestore['conversationHistory'] = []
            
            task_data_firestore['conversationHistory'].append({
                'userMessage': user_response_for_langgraph,
                'agentResponse': result.get('question', ''),
                'timestamp': timestamp or task_data_firestore.get('lastUpdated')
            })
            
            # Update task status
            task_data_firestore['lastUpdated'] = timestamp or task_data_firestore.get('lastUpdated')
            if result.get('is_complete'):
                task_data_firestore['status'] = 'completed'
            
            # Save updated task data
            if user_email == 'foilboi@gmail.com':
                task_key = create_task_key(processing_email, task_title)
            else:
                existing_task = find_existing_task(user_email, task_title)
                task_key = existing_task['taskKey'] if existing_task else create_task_key(user_email, task_title)
            
            task_agent_state = {
                'agentStateKey': task_key,
                'currentTask': task_data_firestore,
                'createdAt': task_data_firestore.get('createdAt'),
                'lastUpdated': task_data_firestore.get('lastUpdated')
            }
            
            db.collection('taskAgent1').document(task_key).set(task_agent_state)
            logger.info(f'💾 Updated task data for {processing_email}')
        
        # Clear lock if it was acquired
        if user_email != 'foilboi@gmail.com':
            clear_email_lock(user_email, task_title)
        
        logger.info(f'✅ Successfully processed email from {user_email}')
        logger.info(f'📤 LangGraph result: {json.dumps(result, indent=2)}')
        
        # TODO: Add email sending logic here if needed
        # For now, just log the result
        
    except Exception as error:
        logger.error(f'❌ Cloud function error in process_email_pubsub: {error}')
        logger.exception("Full traceback:")

def parse_foilboi_email_body(email_body):
    """Parse the structured email body from foilboi@gmail.com"""
    try:
        # The email body contains structured data in a specific format
        # We need to extract key-value pairs from the text
        
        task_data = {}
        
        # Split the email body into lines
        lines = email_body.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('---'):
                i += 1
                continue
                
            # Look for key-value patterns
            if ':' in line:
                # Handle different formats
                if line.startswith('CustomerName:'):
                    task_data['CustomerName'] = line.split(':', 1)[1].strip().rstrip(',')
                elif '"custemail"' in line:
                    # Extract email from "custemail": richard.genet@gmail.com ,
                    email_match = line.split('"custemail"')[1].strip()
                    if ':' in email_match:
                        email = email_match.split(':', 1)[1].strip().rstrip(',').strip('"')
                        task_data['custemail'] = email
                elif '"Posted"' in line:
                    task_data['Posted'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"DueDate"' in line:
                    task_data['DueDate'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"Task"' in line:
                    task_data['Task'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"description"' in line:
                    task_data['description'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"Category"' in line:
                    task_data['Category'] = line.split(':', 1)[1].strip().rstrip(',').strip('"{}')
                elif '"FullAddress"' in line:
                    task_data['FullAddress'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"Task Budget"' in line:
                    task_data['Task Budget'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"State"' in line:
                    task_data['State'] = line.split(':', 1)[1].strip().rstrip(',').strip('"')
                elif '"vendors"' in line:
                    # Vendors section is multi-line, so we need to capture all content until the closing brace
                    vendors_start = line.find('"vendors"')
                    if vendors_start != -1:
                        # Get the initial content from this line
                        initial_content = line[vendors_start:].split(':', 1)[1].strip()
                        vendors_content = [initial_content]
                        
                        # Continue reading lines until we find the closing brace
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            vendors_content.append(next_line)
                            
                            # Check if this line contains the closing brace
                            if '}' in next_line:
                                break
                            i += 1
                        
                        # Join all the vendors content
                        task_data['vendors'] = '\n'.join(vendors_content)
                        i += 1  # Move to next line after processing vendors
                        continue
            
            i += 1
        
        # Validate that we have the essential fields
        if not task_data.get('custemail') or not task_data.get('Task'):
            logger.error(f'❌ Missing essential fields in parsed task data: {task_data}')
            return None
        
        logger.info(f'✅ Successfully parsed task data: {json.dumps(task_data, indent=2)}')
        return task_data
        
    except Exception as error:
        logger.error(f'❌ Error parsing foilboi email body: {error}')
        logger.exception("Full traceback:")
        return None 