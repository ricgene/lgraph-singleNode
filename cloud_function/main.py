import base64
import json
import os
import time
import random
from google.cloud import firestore
import requests
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from datetime import datetime
import functions_framework
from flask import Request, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the agent logic
from agent import run_agent_turn

# TODO: Import your LangGraph agent here
# from your_langgraph_module import run_langgraph_agent

# Firestore client
firestore_client = firestore.Client()

# Distributed lock logic
def acquire_email_lock(customer_email, task_title):
    doc_ref = firestore_client.collection('taskAgent1').document(customer_email)
    try:
        doc = doc_ref.get()
        data = doc.to_dict() if doc.exists else {"tasks": {}}
    except Exception as e:
        print(f"Error getting document: {e}")
        data = {"tasks": {}}

    task = data.get("tasks", {}).get(task_title, {})
    if "emailLock" not in task:
        task["emailLock"] = None

    # Wait random 0-1s
    wait_time = random.uniform(0, 1)
    print(f"⏳ Waiting {int(wait_time*1000)}ms before attempting lock acquisition")
    time.sleep(wait_time)

    # Re-fetch the document to get the latest state after waiting
    try:
        doc = doc_ref.get()
        data = doc.to_dict() if doc.exists else {"tasks": {}}
        task = data.get("tasks", {}).get(task_title, {})
    except Exception as e:
        print(f"Error re-fetching document: {e}")
        return None

    last4 = str(int(time.time() * 1000))[-4:]
    print(f"🔒 Attempting to acquire lock with digits: {last4}")

    if task.get("emailLock") is not None:
        print(f"🚫 Lock already taken: {task['emailLock']}")
        return None

    # Initialize task if it doesn't exist
    if not data.get("tasks", {}).get(task_title):
        data.setdefault("tasks", {})[task_title] = {
            "taskStartConvo": [],
            "emailLock": None,
            "status": "active",
            "lastMsgSent": None,
            "taskInfo": {
                "title": task_title,
                "description": "Task initiated via email",
                "priority": "medium",
                "assignedAgent": "taskAgent1"
            }
        }
    
    data["tasks"][task_title]["emailLock"] = last4
    doc_ref.set(data)
    
    # Verify
    time.sleep(0.1) # Give a moment for write to propagate
    doc = doc_ref.get()
    verify = doc.to_dict().get("tasks", {}).get(task_title, {}).get("emailLock")
    if verify == last4:
        print(f"✅ Lock acquired: {last4}")
        return last4
        
    print(f"❌ Lock verification failed. Expected: {last4}, Got: {verify}")
    return None

def clear_email_lock(customer_email, task_title):
    doc_ref = firestore_client.collection('taskAgent1').document(customer_email)
    try:
        doc = doc_ref.get()
        if not doc.exists:
            return
        data = doc.to_dict()
        if task_title in data.get("tasks", {}):
            data["tasks"][task_title]["emailLock"] = None
            doc_ref.set(data)
            print(f"🔓 Cleared email lock for {customer_email} - {task_title}")
    except Exception as e:
        print(f"Error clearing lock: {e}")

# Firestore data handling functions
def load_task_agent_state(customer_email):
    try:
        doc_ref = firestore_client.collection('taskAgent1').document(customer_email)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return {"customerEmail": customer_email, "tasks": {}}
    except Exception as e:
        print(f"Error loading task agent state: {e}")
        return {"customerEmail": customer_email, "tasks": {}}

def save_task_agent_state(customer_email, state):
    try:
        doc_ref = firestore_client.collection('taskAgent1').document(customer_email)
        doc_ref.set(state)
    except Exception as e:
        print(f"Error saving task agent state: {e}")

def add_conversation_turn(customer_email, task_title, user_message, agent_response, is_complete=False):
    state = load_task_agent_state(customer_email)
    task = state.setdefault("tasks", {}).setdefault(task_title, {
        "taskStartConvo": [],
        "emailLock": None,
        "status": "active",
        "lastMsgSent": None,
        "taskInfo": {
            "title": task_title,
            "description": "Task initiated via email",
            "priority": "medium",
            "assignedAgent": "taskAgent1"
        }
    })
    
    turn_number = len(task["taskStartConvo"]) + 1
    turn = {
        "userMessage": user_message,
        "agentResponse": agent_response,
        "turnNumber": turn_number,
        "isComplete": is_complete,
        "conversationId": f"{customer_email}-{task_title}-{int(time.time() * 1000)}"
    }
    
    task["taskStartConvo"].append(turn)
    if is_complete:
        task["status"] = "completed"
        
    save_task_agent_state(customer_email, state)
    return turn

def should_send_response(customer_email, task_title, question_number):
    # For the new static subject line approach, always send responses
    # unless the conversation is complete
    state = load_task_agent_state(customer_email)
    task = state.get("tasks", {}).get(task_title)
    
    if not task:
        return True
        
    # Check if the last turn was marked as complete
    conversation_turns = task.get("taskStartConvo", [])
    if conversation_turns and conversation_turns[-1].get("isComplete"):
        print(f"🚫 Conversation is complete for {customer_email} - {task_title}")
        return False
        
    return True

def update_last_msg_sent(customer_email, task_title, subject, body):
    state = load_task_agent_state(customer_email)
    task = state.get("tasks", {}).get(task_title)
    if not task:
        return False

    import hashlib
    message_hash = hashlib.md5(f"{subject}{body}".encode()).hexdigest()

    if task.get("lastMsgSent") and task["lastMsgSent"].get("messageHash") == message_hash:
        print(f"🚫 Duplicate message detected for {customer_email} - {task_title}")
        return False
        
    task["lastMsgSent"] = {
        "subject": subject,
        "body": body,
        "messageHash": message_hash,
        "turnNumber": len(task["taskStartConvo"])
    }
    
    save_task_agent_state(customer_email, state)
    print(f"✅ Updated lastMsgSent for {customer_email} - {task_title}")
    return True

def send_email_via_gcp(recipient_email: str, subject: str, body: str) -> bool:
    """Sends an email by calling the deployed GCP email function."""
    email_function_url = os.getenv('EMAIL_FUNCTION_URL', 'https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple')
    if not email_function_url:
        logger.error("❌ EMAIL_FUNCTION_URL not found in environment variables.")
        return False
    try:
        payload = {"to": recipient_email, "subject": subject, "body": body}
        logger.info(f"📧 Sending email to {recipient_email} with subject: {subject}")
        response = requests.post(email_function_url, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info(f"✅ Email sent successfully to {recipient_email}")
            return True
        else:
            logger.error(f"❌ Email function returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error calling email function: {e}")
        return False

# Main entry point for Pub/Sub-triggered Cloud Function
def process_email_pubsub(event, context):
    print('📧 Cloud Function triggered via Pub/Sub')
    if 'data' not in event:
        print('No data in event')
        return

    try:
        # Pub/Sub automatically base64 encodes the message data
        payload = base64.b64decode(event['data']).decode('utf-8')
        print(f'📧 Raw payload: {payload}')
        message = json.loads(payload)
        print(f'📧 Parsed message: {message}')
    except Exception as e:
        print(f'Error decoding Pub/Sub message: {e}')
        print(f'Event data: {event.get("data", "No data")}')
        return

    user_email = message.get('userEmail')
    user_response = message.get('userResponse')
    task_title = message.get('taskTitle', 'Prizm Task Question')

    if not user_email or not user_response:
        print('Missing required fields: userEmail, userResponse')
        print(f'Received message: {message}')
        return

    print(f'Processing: {user_email} | Task: {task_title}')
    
    # Create or get task record with new key structure
    task_id, agent_state_key = create_or_get_task_record(user_email, task_title)
    
    lock = acquire_email_lock(user_email, task_title)
    if not lock:
        print(f'Could not acquire lock for {user_email}, another instance is processing.')
        return

    try:
        # Load conversation state from Firestore using the new agent state key
        task_state = load_task_agent_state_by_key(agent_state_key)
        previous_agent_state = task_state.get("currentTask", {})
        print(f"🔍 Loaded previous agent state: {previous_agent_state}")

        # Run the agent for one turn
        print(f"🤖 Calling run_agent_turn with user_input: '{user_response}'")
        agent_result = run_agent_turn(
            user_input=user_response,
            previous_state=previous_agent_state,
            user_email=user_email
        )
        print(f"🤖 Agent result: {agent_result}")

        # Save the new conversation state with task reference
        add_conversation_turn_with_task(
            task_id=task_id,
            user_email=user_email,
            task_title=task_title,
            user_message=user_response,
            agent_response=agent_result.get("question", ""),
            is_complete=agent_result.get("is_complete", False)
        )

        # Decide whether to send a response
        if agent_result.get("question") and not agent_result.get("is_complete"):
            print(f"📧 Should send response: {agent_result.get('question')}")
            if should_send_response_by_task(task_id):
                # Get the current turn number for the subject line
                task_ref = firestore_client.collection('tasks').document(task_id)
                task_doc = task_ref.get()
                if task_doc.exists:
                    task_data = task_doc.to_dict()
                    # Count agent responses to get the correct turn number
                    agent_response_count = sum(1 for turn in task_data.get('conversationHistory', []) if turn.get('agentResponse'))
                    turn_number = agent_response_count + 1
                else:
                    turn_number = 1
                
                subject = f"Prizm Task Question"
                body = f"Hello!\n\nHelen from Prizm here. I have a question about your task:\n\n{agent_result['question']}\n\nPlease reply to this email."
                
                if update_last_msg_sent_by_task(task_id, subject, body):
                    # Clear lock just before sending
                    clear_email_lock(user_email, task_title)
                    print(f"📧 Sending email to {user_email}")
                    send_email_via_gcp(user_email, subject, body)
                else:
                    print("Skipping email send due to duplicate detection.")
            else:
                print("Skipping email send due to conversation completion.")
        else:
            print(f"🚫 Not sending response - question: {agent_result.get('question')}, is_complete: {agent_result.get('is_complete')}")

    except Exception as e:
        print(f"❌ An error occurred during processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always ensure the lock is eventually cleared
        clear_email_lock(user_email, task_title)
        print('✅ Processing complete.')

def create_or_get_task_record(user_email, task_title):
    """
    Create a new task record or get existing one with the key structure: userEmail,taskTitle,timestamp
    """
    # For now, always create a new task to avoid confusion with existing conversations
    # In the future, we could add logic to detect if we're continuing the same conversation
    # by checking the last message timestamp or conversation state
    
    # Create new task record
    timestamp = datetime.now().isoformat()
    task_id = f"{user_email}_{task_title}_{timestamp}"
    agent_state_key = f"taskAgent1_{user_email}_{task_title}_{timestamp}"
    
    task_data = {
        "taskId": task_id,
        "userEmail": user_email,
        "taskTitle": task_title,
        "taskDescription": f"Task initiated via email conversation",
        "taskType": "home_improvement",
        "createdAt": timestamp,
        "status": "active",
        "agentStateKey": agent_state_key,
        "metadata": {
            "version": "1.0",
            "createdBy": "email_system",
            "lastUpdated": timestamp
        }
    }
    
    # Add to tasks collection
    task_ref = firestore_client.collection('tasks').document(task_id)
    task_ref.set(task_data)
    
    logger.info(f"✅ Created new task record: {task_id}")
    return task_id, agent_state_key

def load_task_agent_state_by_key(agent_state_key):
    """
    Load agent state using the new key structure - make it task-specific
    """
    try:
        # Use the full agent_state_key as the document key to make it task-specific
        doc_ref = firestore_client.collection('taskAgent1').document(agent_state_key)
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            # Initialize new state
            return {
                "currentTask": {},
                "agentStateKey": agent_state_key,
                "createdAt": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"Error loading task agent state: {e}")
        return {"currentTask": {}}

def add_conversation_turn_with_task(task_id, user_email, task_title, user_message, agent_response, is_complete=False):
    """
    Add conversation turn with task reference
    """
    # Get the task document
    task_ref = firestore_client.collection('tasks').document(task_id)
    task_doc = task_ref.get()
    
    if not task_doc.exists:
        print(f"❌ Task {task_id} not found")
        return
    
    task_data = task_doc.to_dict()
    
    # Initialize conversation history if it doesn't exist
    if 'conversationHistory' not in task_data:
        task_data['conversationHistory'] = []
    
    # Calculate turn number based on agent responses (questions) only
    # Count how many agent responses we've sent so far
    agent_response_count = sum(1 for turn in task_data['conversationHistory'] if turn.get('agentResponse'))
    turn_number = agent_response_count + 1
    
    turn = {
        "userMessage": user_message,
        "agentResponse": agent_response,
        "turnNumber": turn_number,
        "isComplete": is_complete,
        "timestamp": datetime.now().isoformat(),
        "conversationId": f"{task_id}-{turn_number}"
    }
    
    task_data['conversationHistory'].append(turn)
    task_data['lastUpdated'] = datetime.now().isoformat()
    
    if is_complete:
        task_data['status'] = 'completed'
    
    # Update the task document
    task_ref.set(task_data)
    
    # Also update the agent state
    agent_state = load_task_agent_state_by_key(task_data['agentStateKey'])
    agent_state['currentTask'] = {
        "taskId": task_id,
        "taskTitle": task_title,
        "lastTurn": turn,
        "status": task_data['status']
    }
    
    save_task_agent_state_by_key(task_data['agentStateKey'], agent_state)
    
    print(f"✅ Added conversation turn {turn_number} to task {task_id}")
    return turn

def save_task_agent_state_by_key(agent_state_key, state):
    """
    Save agent state using the new key structure - make it task-specific
    """
    try:
        # Use the full agent_state_key as the document key to make it task-specific
        doc_ref = firestore_client.collection('taskAgent1').document(agent_state_key)
        doc_ref.set(state, merge=True)
    except Exception as e:
        print(f"Error saving task agent state: {e}")

def should_send_response_by_task(task_id):
    """
    Check if we should send a response for this task
    """
    task_ref = firestore_client.collection('tasks').document(task_id)
    task_doc = task_ref.get()
    
    if not task_doc.exists:
        return True
    
    task_data = task_doc.to_dict()
    
    # Check if the task is completed
    if task_data.get('status') == 'completed':
        print(f"🚫 Task {task_id} is completed")
        return False
    
    # Check if the last turn was marked as complete
    conversation_history = task_data.get('conversationHistory', [])
    if conversation_history and conversation_history[-1].get('isComplete'):
        print(f"🚫 Last conversation turn was marked complete for task {task_id}")
        return False
    
    return True

def update_last_msg_sent_by_task(task_id, subject, body):
    """
    Update last message sent for a specific task
    """
    import hashlib
    
    task_ref = firestore_client.collection('tasks').document(task_id)
    task_doc = task_ref.get()
    
    if not task_doc.exists:
        return True  # Allow sending if task doesn't exist
    
    task_data = task_doc.to_dict()
    message_hash = hashlib.md5(f"{subject}{body}".encode()).hexdigest()
    
    if task_data.get('lastMsgSent') and task_data['lastMsgSent'].get('messageHash') == message_hash:
        print(f"🚫 Duplicate message detected for task {task_id}")
        return False
    
    task_data['lastMsgSent'] = {
        "subject": subject,
        "body": body,
        "messageHash": message_hash,
        "timestamp": datetime.now().isoformat()
    }
    
    task_ref.set(task_data, merge=True)
    print(f"✅ Updated lastMsgSent for task {task_id}")
    return True

# Entry point for Google Cloud Functions
# In your deployment, set entry_point to 'process_email_pubsub' 

# HTTP Webhook endpoint for receiving messages
@functions_framework.http
def process_message_http(request: Request):
    """
    HTTP webhook endpoint for receiving messages from various sources
    (SMS, web forms, etc.)
    """
    try:
        # Handle CORS preflight requests
        if request.method == 'OPTIONS':
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '3600'
            }
            return ('', 204, headers)
        
        if request.method != 'POST':
            return jsonify({'error': 'Method not allowed'}), 405
        
        # Parse the request
        request_json = request.get_json(silent=True)
        if not request_json:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Handle both old format and new format
        if 'custemail' in request_json:
            # Old format: Customer Name, custemail, Task, description, etc.
            user_email = request_json.get('custemail')
            customer_name = request_json.get('Customer Name', 'Unknown')
            task_title = request_json.get('Task', 'General Task')
            description = request_json.get('description', '')
            category = request_json.get('Category', '')
            full_address = request_json.get('Full Address', '')
            task_budget = request_json.get('Task Budget', 0)
            state = request_json.get('State', '')
            vendors = request_json.get('vendors', '')
            
            # Combine description and vendors as the user message
            user_message = f"Task: {task_title}\nDescription: {description}\nCategory: {category}\nAddress: {full_address}\nBudget: ${task_budget}\nState: {state}\nVendor Request: {vendors}"
            
            source = 'web_form'
        else:
            # New format: user_email, message, task_title
            user_email = request_json.get('user_email')
            user_message = request_json.get('message')
            task_title = request_json.get('task_title', 'General Task')
            source = request_json.get('source', 'http_webhook')
        
        if not user_email or not user_message:
            return jsonify({'error': 'Missing required fields: custemail or user_email, and message/description'}), 400
        
        logger.info(f"📨 Received {source} message from {user_email}: {user_message[:50]}...")
        
        # Create or get task record
        task_id, agent_state_key = create_or_get_task_record(user_email, task_title)
        
        # Load current agent state
        agent_state = load_task_agent_state_by_key(agent_state_key)
        
        # Build conversation history from task's conversation history
        task_ref = firestore_client.collection('tasks').document(task_id)
        task_doc = task_ref.get()
        conversation_history = ""
        
        if task_doc.exists:
            task_data = task_doc.to_dict()
            # Build conversation history from previous turns
            for turn in task_data.get('conversationHistory', []):
                if turn.get('userMessage'):
                    conversation_history += f"User: {turn['userMessage']}\n"
                if turn.get('agentResponse'):
                    conversation_history += f"Agent: {turn['agentResponse']}\n"
            
            logger.info(f"📝 Built conversation history from {len(task_data.get('conversationHistory', []))} turns")
            logger.info(f"📝 Conversation history: {conversation_history[:200]}...")
        else:
            logger.info(f"📝 No existing task found, starting fresh conversation")
        
        # Create proper previous state for the agent
        previous_state = {
            'conversation_history': conversation_history,
            'is_complete': agent_state.get('currentTask', {}).get('is_complete', False),
            'user_email': user_email
        }
        
        logger.info(f"📝 Previous state conversation history length: {len(previous_state['conversation_history'])} characters")
        
        # Check if we should send a response
        if not should_send_response_by_task(task_id):
            return jsonify({
                'status': 'no_response_needed',
                'message': 'Conversation is complete or response not needed',
                'task_id': task_id
            }), 200
        
        # Run the agent with correct parameters
        logger.info(f"🤖 Running agent for task {task_id}")
        logger.info(f"📝 Conversation history length: {len(conversation_history)} characters")
        agent_result = run_agent_turn(
            user_input=user_message,
            previous_state=previous_state,
            user_email=user_email
        )
        
        # Extract the agent's question from the result
        agent_response = agent_result.get('question', 'I apologize, but I encountered an issue processing your message.')
        is_complete = agent_result.get('is_complete', False)
        
        # Add conversation turn
        turn = add_conversation_turn_with_task(
            task_id, user_email, task_title, user_message, agent_response, is_complete
        )
        
        # Update agent state with the new conversation history
        agent_state['currentTask'] = {
            'conversation_history': agent_result.get('conversation_history', ''),
            'is_complete': is_complete,
            'user_email': user_email,
            'taskId': task_id,
            'taskTitle': task_title
        }
        save_task_agent_state_by_key(agent_state_key, agent_state)
        
        logger.info(f"📝 Updated agent state with conversation history length: {len(agent_result.get('conversation_history', ''))} characters")
        logger.info(f"📝 Agent response: {agent_response[:100]}...")
        
        # Check if response should be sent
        if agent_response and agent_response.strip():
            # Send email if response is generated
            subject = f"Prizm Task Question"
            email_body = f"""Hello!

Helen from Prizm here. I have a question about your task:

{agent_response}

Please reply to this email."""
            
            logger.info(f"📧 Preparing to send email to {user_email}")
            logger.info(f"📧 Subject: {subject}")
            logger.info(f"📧 Body preview: {email_body[:100]}...")
            
            # Check if we should send this email (avoid duplicates)
            if update_last_msg_sent_by_task(task_id, subject, email_body):
                logger.info(f"📧 Sending email - no duplicate detected")
                email_sent = send_email_via_gcp(user_email, subject, email_body)
                if email_sent:
                    logger.info(f"📧 Email sent successfully to {user_email} for task {task_id}")
                else:
                    logger.error(f"❌ Failed to send email to {user_email} for task {task_id}")
            else:
                logger.info(f"🚫 Skipping duplicate email for task {task_id}")
            
            # For HTTP webhook, we return the response directly
            # For SMS, you would call your SMS service here
            response_data = {
                'status': 'success',
                'task_id': task_id,
                'agent_response': agent_response,
                'turn_number': turn['turnNumber'] if turn else 1,
                'should_send_response': True,
                'is_complete': is_complete,
                'email_sent': email_sent if 'email_sent' in locals() else False
            }
            
            logger.info(f"✅ Processed {source} message for task {task_id}")
            logger.info(f"📊 Response data: {response_data}")
            return jsonify(response_data), 200
        else:
            return jsonify({
                'status': 'no_response',
                'task_id': task_id,
                'message': 'Agent did not generate a response'
            }), 200
            
    except Exception as e:
        logger.error(f"❌ Error processing HTTP message: {e}")
        return jsonify({'error': str(e)}), 500

# For local testing with functions framework
if __name__ == "__main__":
    import functions_framework
    
    @functions_framework.cloud_event
    def test_function(cloud_event):
        # Convert cloud event to Pub/Sub event format
        event = {
            'data': cloud_event.data.get('message', {}).get('data', '')
        }
        context = None
        return process_email_pubsub(event, context)

# Cloud Run compatibility - Flask app
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def cloud_run_http_handler():
    """Cloud Run HTTP handler that wraps the Cloud Function logic"""
    return process_message_http(request)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({'status': 'healthy'}), 200

# For Cloud Run deployment
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port) 