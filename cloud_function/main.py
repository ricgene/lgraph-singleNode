import base64
import json
import os
import time
import random
from google.cloud import firestore
import requests

# TODO: Import your LangGraph agent here
# from your_langgraph_module import run_langgraph_agent

# Firestore client
firestore_client = firestore.Client()

# Distributed lock logic
async def acquire_email_lock(customer_email, task_title):
    doc_ref = firestore_client.collection('taskAgent1').document(customer_email)
    doc = doc_ref.get()
    data = doc.to_dict() if doc.exists else {"tasks": {}}
    task = data["tasks"].get(task_title, {})
    if "emailLock" not in task:
        task["emailLock"] = None
    # Wait random 0-1s
    wait_time = random.uniform(0, 1)
    print(f"⏳ Waiting {int(wait_time*1000)}ms before attempting lock acquisition")
    time.sleep(wait_time)
    last4 = str(int(time.time() * 1000))[-4:]
    print(f"🔒 Attempting to acquire lock with digits: {last4}")
    if task.get("emailLock") is not None:
        print(f"🚫 Lock already taken: {task['emailLock']}")
        return None
    task["emailLock"] = last4
    data["tasks"][task_title] = task
    doc_ref.set(data)
    # Verify
    doc = doc_ref.get()
    verify = doc.to_dict()["tasks"][task_title]["emailLock"]
    if verify == last4:
        print(f"✅ Lock acquired: {last4}")
        return last4
    print(f"❌ Lock verification failed. Expected: {last4}, Got: {verify}")
    return None

def clear_email_lock(customer_email, task_title):
    doc_ref = firestore_client.collection('taskAgent1').document(customer_email)
    doc = doc_ref.get()
    data = doc.to_dict() if doc.exists else {"tasks": {}}
    if task_title in data["tasks"]:
        data["tasks"][task_title]["emailLock"] = None
        doc_ref.set(data)
        print(f"🔓 Cleared email lock for {customer_email} - {task_title}")

# Main entry point for Pub/Sub-triggered Cloud Function
def process_email_pubsub(event, context):
    print('📧 Cloud Function triggered via Pub/Sub')
    if 'data' not in event:
        print('No data in event')
        return
    payload = base64.b64decode(event['data']).decode('utf-8')
    try:
        message = json.loads(payload)
    except Exception as e:
        print(f'Error decoding message: {e}')
        return
    user_email = message.get('userEmail')
    user_response = message.get('userResponse')
    task_title = message.get('taskTitle', 'Prizm Task Question')
    if not user_email or not user_response:
        print('Missing required fields: userEmail, userResponse')
        return
    print(f'Processing email from: {user_email}')
    print(f'User response: {user_response}')
    print(f'Task title: {task_title}')
    # Acquire lock
    lock = acquire_email_lock(user_email, task_title)
    if not lock:
        print('Another responder is processing this email.')
        return
    # TODO: Load conversation from Firestore
    # TODO: Run LangGraph agent (call run_langgraph_agent or similar)
    # TODO: Save conversation turn to Firestore
    # TODO: Check for duplicate/shouldSend logic
    # TODO: Clear lock just before sending
    # TODO: Send response via GCP email function (requests.post to EMAIL_FUNCTION_URL)
    clear_email_lock(user_email, task_title)
    print('✅ Processing complete')

# Entry point for Google Cloud Functions
# In your deployment, set entry_point to 'process_email_pubsub' 