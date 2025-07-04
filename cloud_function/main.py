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
    return f"{user_email}_{task_title}_{timestamp}"

# Helper function to create task ID
def create_task_id(user_email, task_title, timestamp=None):
    if not timestamp:
        from datetime import datetime
        timestamp = datetime.now().isoformat()
    return f"{user_email}_{task_title}_{timestamp}"

# Helper function to find existing task
def find_existing_task(user_email, task_title):
    try:
        task_agent_ref = db.collection('conversations')
        docs = task_agent_ref.stream()
        
        for doc in docs:
            data = doc.to_dict()
            if (data.get('userEmail') == user_email and 
                data.get('taskTitle') == task_title and
                data.get('status') != 'completed'):
                return {
                    'taskKey': doc.id,
                    'taskData': data
                }
        
        return None
    except Exception as error:
        logger.error(f'Error finding existing task: {error}')
        return None

# Helper function to create new task
def create_new_task(user_email, task_title, user_first_name=None):
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    task_key = create_task_key(user_email, task_title, timestamp)
    task_id = create_task_id(user_email, task_title, timestamp)
    
    conversation_state = {
        'taskId': task_id,
        'taskTitle': task_title,
        'userEmail': user_email,
        'userFirstName': user_first_name or user_email.split('@')[0],
        'createdAt': timestamp,
        'lastUpdated': timestamp,
        'status': 'active',
        'conversationHistory': [],
        'fullInputHistory': []  # Store complete input to agent each time
    }
    
    db.collection('conversations').document(task_key).set(conversation_state)
    logger.info(f'✅ Created new conversation: {task_id} with key: {task_key}')
    
    return {
        'taskKey': task_key,
        'taskData': conversation_state
    }

# LangGraph processing function
def process_user_response(user_email, user_response, conversation_state, user_first_name=None, task_title=None):
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
        
        # Create input data with user first name and task name included
        input_data = {
            "user_input": user_response,
            "user_first_name": user_first_name or user_email.split('@')[0],
            "task_name": task_title or "Task",
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
            logger.info(f"📊 Graph output contains {len(graph_output)} chunks")
            
            # Look for the final response in the graph output
            final_response = None
            
            # First, try to find a chunk with the expected format
            for chunk in reversed(graph_output):
                logger.info(f"🔍 Examining chunk: {type(chunk)} - {chunk}")
                if isinstance(chunk, dict):
                    if "question" in chunk:
                        final_response = chunk
                        logger.info(f"✅ Found response with question: {chunk}")
                        break
                    elif "output" in chunk and isinstance(chunk["output"], dict) and "question" in chunk["output"]:
                        final_response = chunk["output"]
                        logger.info(f"✅ Found response in output: {chunk['output']}")
                        break
                    elif "value" in chunk and isinstance(chunk["value"], dict) and "question" in chunk["value"]:
                        final_response = chunk["value"]
                        logger.info(f"✅ Found response in value: {chunk['value']}")
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
                # Try to extract any meaningful response from the chunks
                logger.warning(f"⚠️ Could not find expected response format in {len(graph_output)} chunks")
                logger.info(f"📋 Available chunks: {[type(chunk) for chunk in graph_output]}")
                
                # Look for any text content in the chunks
                text_content = ""
                for chunk in graph_output:
                    if isinstance(chunk, dict):
                        if "text" in chunk:
                            text_content = chunk["text"]
                            break
                        elif "content" in chunk:
                            text_content = chunk["content"]
                            break
                        elif "message" in chunk:
                            text_content = chunk["message"]
                            break
                
                if text_content:
                    response_data = {
                        "question": text_content,
                        "conversation_history": conversation_state.get("conversation_history", ""),
                        "is_complete": False,
                        "completion_state": "OTHER",
                        "user_email": user_email
                    }
                    logger.info(f"📝 Using extracted text content: {text_content[:100]}...")
                else:
                    # Fallback if we can't find any meaningful response
                    response_data = {
                        "question": "I've received your task request and will start processing it. Please wait for my next response.",
                        "conversation_history": conversation_state.get("conversation_history", ""),
                        "is_complete": False,
                        "completion_state": "OTHER",
                        "user_email": user_email
                    }
                    logger.warning(f"⚠️ No meaningful content found, using fallback response")
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
        error_message = str(error)
        logger.error(f"❌ Error processing with LangGraph for {user_email}: {error_message}")
        
        # Check if it's a quota/rate limit error
        if "quota" in error_message.lower() or "rate limit" in error_message.lower() or "429" in error_message:
            logger.warning(f"⚠️ OpenAI quota/rate limit detected for {user_email}")
            return {
                "question": "I'm currently experiencing high demand and my processing capacity is temporarily limited. Your task has been received and stored. I'll process it as soon as possible.",
                "conversation_history": conversation_state.get("conversation_history", ""),
                "is_complete": False,
                "completion_state": "QUOTA_EXCEEDED",
                "user_email": user_email
            }
        
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
        result = process_user_response(user_email, user_response, temp_conversation_state, task_title=task_title)
        
        if not result:
            logger.info(f'❌ LangGraph processing failed for {user_email}')
            return (json.dumps({
                'success': False,
                'message': 'Failed to process with LangGraph'
            }), 500, response_headers)
        
        # For now, just return success without email sending
        # You can add email sending logic here later
        
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
I have a new task request for you to process:

Customer: {customer_name} ({customer_email})
Task: {task_number} - {category}
Description: {task_description}
Due Date: {due_date}
State: {state}

Please start the conversation to help this customer with their task.
"""
            
            # For the first call, we don't need to check for existing tasks
            # Just create a new task and start the workflow
            new_task = create_new_task(customer_email, task_title, user_first_name=customer_name.split()[0] if customer_name else None)
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
        result = process_user_response(processing_email, user_response_for_langgraph, conversation_state, task_title=task_title)
        
        if not result:
            logger.error(f'❌ LangGraph processing failed for {processing_email}')
            # Create a fallback response when LangGraph fails
            fallback_result = {
                "question": "I'm currently experiencing technical difficulties with my AI processing. Your task has been received and stored. I'll process it as soon as possible.",
                "conversation_history": conversation_state.get("conversation_history", ""),
                "is_complete": False,
                "completion_state": "QUOTA_EXCEEDED",
                "user_email": processing_email
            }
            logger.info(f'📝 Using fallback response due to LangGraph failure: {json.dumps(fallback_result, indent=2)}')
            result = fallback_result
        
        # Update task with conversation history and full input history
        if task_data_firestore:
            # Add the new conversation turn
            if 'conversationHistory' not in task_data_firestore:
                task_data_firestore['conversationHistory'] = []
            
            # Use current timestamp for this turn
            from datetime import datetime
            current_timestamp = datetime.now().isoformat()
            
            task_data_firestore['conversationHistory'].append({
                'userMessage': user_response_for_langgraph,
                'agentResponse': result.get('question', ''),
                'timestamp': current_timestamp
            })
            
            # Store the full input to the agent (grows each time)
            if 'fullInputHistory' not in task_data_firestore:
                task_data_firestore['fullInputHistory'] = []
            
            # Extract user first name properly
            user_first_name = task_data_firestore.get('userFirstName')
            if not user_first_name:
                # Try to extract from customer name if available
                if task_data_firestore.get('customerName'):
                    user_first_name = task_data_firestore['customerName'].split()[0]
                else:
                    # Fallback to email prefix
                    user_first_name = processing_email.split('@')[0]
            
            # Create the full input that was sent to the agent
            full_input = {
                "user_input": user_response_for_langgraph,
                "user_first_name": user_first_name,
                "task_name": task_title,
                "previous_state": {
                    "conversation_history": conversation_state.get("conversation_history", ""),
                    "is_complete": conversation_state.get("is_complete", False),
                    "user_email": processing_email
                }
            }
            
            task_data_firestore['fullInputHistory'].append({
                'input': full_input,
                'timestamp': current_timestamp,
                'turn_number': len(task_data_firestore['fullInputHistory']) + 1
            })
            
            # Update task status
            task_data_firestore['lastUpdated'] = current_timestamp
            if result.get('is_complete'):
                task_data_firestore['status'] = 'completed'
            
            # Save updated task data
            if user_email == 'foilboi@gmail.com':
                task_key = create_task_key(processing_email, task_title)
            else:
                existing_task = find_existing_task(user_email, task_title)
                task_key = existing_task['taskKey'] if existing_task else create_task_key(user_email, task_title)
            
            db.collection('conversations').document(task_key).set(task_data_firestore)
            logger.info(f'💾 Updated conversation data for {processing_email}')
            logger.info(f'📊 Full input history now has {len(task_data_firestore["fullInputHistory"])} entries')
        
        logger.info(f'✅ Successfully processed email from {user_email}')
        logger.info(f'📤 LangGraph result: {json.dumps(result, indent=2)}')
        
        # Send email response to user
        if result and result.get('question'):
            email_subject = "Prizm Task Update"
            email_body = f"""
Hello,

{result['question']}

Best regards,
Prizm Agent
            """.strip()
            
            # Determine the correct email address to send to
            if user_email == 'foilboi808@gmail.com' and task_data_firestore and task_data_firestore.get('userEmail'):
                # For emails from foilboi808, send to the customer email stored in the task
                recipient_email = task_data_firestore['userEmail']
                logger.info(f'📧 Sending response to customer email: {recipient_email}')
            else:
                # For direct customer emails, send back to the same email
                recipient_email = user_email
                logger.info(f'📧 Sending response to user email: {recipient_email}')
            
            # Send email to the correct recipient
            email_sent = send_email_via_gcp(recipient_email, email_subject, email_body)
            if email_sent:
                logger.info(f'📧 Email response sent successfully to {recipient_email}')
            else:
                logger.error(f'❌ Failed to send email response to {recipient_email}')
        else:
            logger.warning(f'⚠️ No question in result to send to {user_email}')
        
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

def send_email_via_gcp(recipient_email: str, subject: str, body: str) -> bool:
    """Sends an email by calling the deployed GCP email function."""
    # Use the environment variable for the email function URL
    email_function_url = os.getenv('EMAIL_FUNCTION_URL', 'https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple')
    if not email_function_url:
        logger.error("❌ EMAIL_FUNCTION_URL not found in environment variables.")
        return False
    try:
        payload = {"to": recipient_email, "subject": subject, "body": body}
        response = requests.post(email_function_url, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info(f"✅ Email sent successfully to {recipient_email}")
            return True
        else:
            logger.error(f"❌ Email function returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending email: {str(e)}")
        return False 