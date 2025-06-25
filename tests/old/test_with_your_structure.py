#!/usr/bin/env python3
"""
Test script using the exact input structure provided by user
"""

import requests
import json
from datetime import datetime

# Server URL
SERVER_URL = "http://localhost:8000"

# Your exact input structure (with corrections)
def get_initial_payload():
    """Get the initial payload with your structure"""
    return {
        "user_input": "I am ready to discuss my home renovation task",  # Added initial message
        "user_email": "test@example.com", 
        "task_json": {
            "taskId": "test@example.com_Kitchen Renovation_2025-06-25T09:55:00",
            "userEmail": "test@example.com",
            "taskTitle": "Kitchen Renovation",
            "taskDescription": "Complete kitchen remodel including cabinets, countertops, and appliances",
            "taskType": "home_improvement",
            "createdAt": "2025-06-25T09:55:00",
            "status": "active",
            "agentStateKey": "taskAgent1_test@example.com_Kitchen Renovation_2025-06-25T09:55:00",
            "metadata": {
                "version": "1.0",
                "createdBy": "test_script",
                "lastUpdated": "2025-06-25T09:55:00"
            }
        },
        "previous_state": None  # Changed to None for fresh start
    }

def get_followup_payload(user_input, previous_state):
    """Get followup payload with conversation state"""
    return {
        "user_input": user_input,
        "user_email": "test@example.com", 
        "task_json": {
            "taskId": "test@example.com_Kitchen Renovation_2025-06-25T09:55:00",
            "userEmail": "test@example.com",
            "taskTitle": "Kitchen Renovation",
            "taskDescription": "Complete kitchen remodel including cabinets, countertops, and appliances",
            "taskType": "home_improvement",
            "createdAt": "2025-06-25T09:55:00",
            "status": "active",
            "agentStateKey": "taskAgent1_test@example.com_Kitchen Renovation_2025-06-25T09:55:00",
            "metadata": {
                "version": "1.0",
                "createdBy": "test_script",
                "lastUpdated": "2025-06-25T09:55:00"
            }
        },
        "previous_state": previous_state
    }

def send_message(payload):
    """Send message to LangGraph server"""
    try:
        response = requests.post(f"{SERVER_URL}/process_message", 
                               json=payload, 
                               headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending message: {e}")
        return None

def test_conversation():
    """Test conversation with your structure"""
    print("🧪 Testing with Your Input Structure")
    print("=" * 50)
    
    # Initial message
    print("🔄 Turn 1 - Initial Message")
    print("-" * 30)
    
    initial_payload = get_initial_payload()
    print(f"📤 Sending initial payload:")
    print(f"   📋 Task: {initial_payload['task_json']['taskTitle']}")
    print(f"   📧 Email: {initial_payload['user_email']}")
    print(f"   💬 Input: {initial_payload['user_input']}")
    
    result = send_message(initial_payload)
    
    if result:
        print(f"✅ Response received:")
        print(f"   🤖 Agent: {result.get('question', 'No response')}")
        print(f"   📊 Complete: {result.get('is_complete', False)}")
        print(f"   📝 History Length: {len(result.get('conversation_history', ''))} chars")
        
        # Update state for next turn
        previous_state = {
            'conversation_history': result.get('conversation_history', ''),
            'is_complete': result.get('is_complete', False),
            'user_email': initial_payload['user_email']
        }
        
        # Follow-up message
        print("\n🔄 Turn 2 - Follow-up Message")
        print("-" * 30)
        
        followup_payload = get_followup_payload("Yes, I will reach out to the contractor", previous_state)
        print(f"📤 Sending followup payload:")
        print(f"   💬 Input: {followup_payload['user_input']}")
        print(f"   📝 Previous State: {len(previous_state['conversation_history'])} chars")
        
        result2 = send_message(followup_payload)
        
        if result2:
            print(f"✅ Response received:")
            print(f"   🤖 Agent: {result2.get('question', 'No response')}")
            print(f"   📊 Complete: {result2.get('is_complete', False)}")
            print(f"   📝 History Length: {len(result2.get('conversation_history', ''))} chars")
        else:
            print("❌ Failed to get followup response")
    else:
        print("❌ Failed to get initial response")

if __name__ == "__main__":
    print("🚀 Testing Your Input Structure")
    print("=" * 30)
    
    # Check server health
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print("❌ Server not responding")
            exit(1)
    except:
        print("❌ Cannot connect to server")
        exit(1)
    
    # Run test
    test_conversation() 