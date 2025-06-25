#!/usr/bin/env python3
"""
Local test script for LangGraph conversation loop with Firestore-like data structure
"""

import requests
import json
import time
from datetime import datetime

# Server URL
SERVER_URL = "http://localhost:8000"

# Example task JSON structure (based on your Firestore schema)
EXAMPLE_TASK_JSON = {
    "taskId": "test@example.com_Home Renovation_2025-06-25T09:45:00",
    "userEmail": "test@example.com",
    "taskTitle": "Home Renovation",
    "taskDescription": "Kitchen and bathroom renovation project",
    "taskType": "home_improvement",
    "createdAt": datetime.now().isoformat(),
    "status": "active",
    "agentStateKey": "taskAgent1_test@example.com_Home Renovation_2025-06-25T09:45:00",
    "metadata": {
        "version": "1.0",
        "createdBy": "test_script",
        "lastUpdated": datetime.now().isoformat()
    }
}

def send_message(user_input, user_email, task_json, previous_state=None):
    """Send a message to the LangGraph server"""
    payload = {
        "user_input": user_input,
        "user_email": user_email,
        "task_json": task_json,
        "previous_state": previous_state
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/process_message", 
                               json=payload, 
                               headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending message: {e}")
        return None

def test_conversation_loop():
    """Test the full conversation loop"""
    print("🧪 Starting LangGraph Conversation Loop Test")
    print("=" * 50)
    
    # Initial state
    user_email = "test@example.com"
    task_json = EXAMPLE_TASK_JSON
    previous_state = None
    
    # Test conversation flow
    conversation_turns = [
        "I am ready to discuss my home renovation task",
        "Yes, I will reach out to the contractor",
        "I have some concerns about the timeline and budget",
        "The timeline is 3 months and budget is $50,000",
        "I want to make sure the contractor is licensed and insured",
        "Yes, I have all the necessary permits",
        "I'm ready to proceed with the project"
    ]
    
    print(f"📋 Task: {task_json['taskTitle']}")
    print(f"👤 User: {user_email}")
    print(f"🔄 Starting conversation loop...\n")
    
    for i, user_input in enumerate(conversation_turns, 1):
        print(f"🔄 Turn {i}/7")
        print(f"👤 User: {user_input}")
        
        # Send message to server
        result = send_message(user_input, user_email, task_json, previous_state)
        
        if result:
            print(f"🤖 Agent: {result.get('question', 'No response')}")
            print(f"📊 Complete: {result.get('is_complete', False)}")
            print(f"📝 History Length: {len(result.get('conversation_history', ''))} chars")
            
            # Update state for next turn
            previous_state = {
                'conversation_history': result.get('conversation_history', ''),
                'is_complete': result.get('is_complete', False),
                'user_email': user_email
            }
            
            # Check if conversation is complete
            if result.get('is_complete', False):
                print("🏁 Conversation completed!")
                break
        else:
            print("❌ Failed to get response from server")
            break
        
        print("-" * 40)
        time.sleep(1)  # Small delay between turns
    
    print("\n✅ Conversation loop test completed!")

def test_health_check():
    """Test server health"""
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

if __name__ == "__main__":
    print("🚀 LangGraph Local Test Script")
    print("=" * 30)
    
    # Check if server is running
    if not test_health_check():
        print("❌ Please start the LangGraph server first:")
        print("   source venv/bin/activate && python langgraph_server.py")
        exit(1)
    
    # Run the conversation test
    test_conversation_loop() 