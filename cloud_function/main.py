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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the agent logic
from agent import run_agent_turn, send_email_via_gcp

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
        payload = base64.b64decode(event['data']).decode('utf-8')
        message = json.loads(payload)
    except Exception as e:
        print(f'Error decoding Pub/Sub message: {e}')
        return

    user_email = message.get('userEmail')
    user_response = message.get('userResponse')
    task_title = message.get('taskTitle', 'Prizm Task Question')

    if not user_email or not user_response:
        print('Missing required fields: userEmail, userResponse')
        return

    print(f'Processing: {user_email} | Task: {task_title}')
    
    lock = acquire_email_lock(user_email, task_title)
    if not lock:
        print(f'Could not acquire lock for {user_email}, another instance is processing.')
        return

    try:
        # Load conversation state from Firestore
        task_state = load_task_agent_state(user_email)
        previous_agent_state = task_state.get("tasks", {}).get(task_title)

        # Run the agent for one turn
        agent_result = run_agent_turn(
            user_input=user_response,
            previous_state=previous_agent_state,
            user_email=user_email
        )

        # Save the new conversation state
        add_conversation_turn(
            customer_email=user_email,
            task_title=task_title,
            user_message=user_response,
            agent_response=agent_result.get("question", ""),
            is_complete=agent_result.get("is_complete", False)
        )

        # Decide whether to send a response
        if agent_result.get("question") and not agent_result.get("is_complete"):
            if should_send_response(user_email, task_title, None):
                subject = "AI Assistant Response"
                body = f"Hello!\n\nHelen from Prizm here. I have a question about your task:\n\n{agent_result['question']}\n\nPlease reply to this email."
                
                if update_last_msg_sent(user_email, task_title, subject, body):
                    # Clear lock just before sending
                    clear_email_lock(user_email, task_title)
                    send_email_via_gcp(user_email, subject, body)
                else:
                    print("Skipping email send due to duplicate detection.")
            else:
                print("Skipping email send due to conversation completion.")

    except Exception as e:
        print(f"An error occurred during processing: {e}")
    finally:
        # Always ensure the lock is eventually cleared
        clear_email_lock(user_email, task_title)
        print('✅ Processing complete.')

# Entry point for Google Cloud Functions
# In your deployment, set entry_point to 'process_email_pubsub' 

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