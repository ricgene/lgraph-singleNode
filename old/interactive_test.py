#!/usr/bin/env python3
"""
Interactive test script for LangGraph conversation loop
User provides task and answers questions interactively
"""

import requests
import json
import time
from datetime import datetime

# Server URL
SERVER_URL = "http://localhost:8000"

def get_task_from_user():
    """Get task details from user input"""
    print("🏠 Welcome to Prizm Task Conversation!")
    print("=" * 40)
    print("Let's create a new task for you...")
    
    task_title = input("📋 Task Title (e.g., 'Kitchen Renovation'): ").strip()
    if not task_title:
        task_title = "Home Improvement Task"
    
    task_description = input("📝 Task Description (e.g., 'Remodel kitchen cabinets and countertops'): ").strip()
    if not task_description:
        task_description = "General home improvement task"
    
    user_email = input("📧 Your Email: ").strip()
    if not user_email:
        user_email = "user@example.com"
    
    # Create task JSON structure
    task_json = {
        "taskId": f"{user_email}_{task_title}_{datetime.now().isoformat()}",
        "userEmail": user_email,
        "taskTitle": task_title,
        "taskDescription": task_description,
        "taskType": "home_improvement",
        "createdAt": datetime.now().isoformat(),
        "status": "active",
        "agentStateKey": f"taskAgent1_{user_email}_{task_title}_{datetime.now().isoformat()}",
        "metadata": {
            "version": "1.0",
            "createdBy": "interactive_test",
            "lastUpdated": datetime.now().isoformat()
        }
    }
    
    print(f"\n✅ Task Created:")
    print(f"   📋 Title: {task_title}")
    print(f"   📝 Description: {task_description}")
    print(f"   📧 Email: {user_email}")
    print(f"   🆔 Task ID: {task_json['taskId']}")
    
    return task_json

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

def interactive_conversation():
    """Run interactive conversation loop"""
    print("\n🔄 Starting Interactive Conversation Loop")
    print("=" * 50)
    
    # Get task from user
    task_json = get_task_from_user()
    user_email = task_json["userEmail"]
    previous_state = None
    
    print(f"\n🤖 Helen (Prizm Agent) will now ask you questions about your task.")
    print(f"💬 You can respond naturally to each question.")
    print(f"🔄 The conversation will continue until complete (max 7 turns).")
    print(f"⏹️  Type 'quit' at any time to exit.\n")
    
    turn_count = 0
    max_turns = 7
    
    while turn_count < max_turns:
        turn_count += 1
        print(f"🔄 Turn {turn_count}/{max_turns}")
        print("-" * 30)
        
        # Get user input
        user_input = input("👤 Your response: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'stop']:
            print("👋 Conversation ended by user.")
            break
        
        if not user_input:
            print("⚠️  Please provide a response.")
            continue
        
        # Send to server
        print("🤖 Processing...")
        result = send_message(user_input, user_email, task_json, previous_state)
        
        if result:
            agent_question = result.get('question', 'No response received')
            is_complete = result.get('is_complete', False)
            
            print(f"🤖 Helen: {agent_question}")
            
            if is_complete:
                print("🏁 Conversation completed!")
                break
            
            # Update state for next turn
            previous_state = {
                'conversation_history': result.get('conversation_history', ''),
                'is_complete': is_complete,
                'user_email': user_email
            }
            
        else:
            print("❌ Failed to get response from server")
            break
        
        print()  # Empty line for readability
    
    if turn_count >= max_turns:
        print("⏰ Maximum turns reached. Conversation ended.")
    
    print("\n✅ Interactive conversation completed!")
    print(f"📊 Total turns: {turn_count}")
    print(f"📋 Task: {task_json['taskTitle']}")

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
    print("🚀 Interactive LangGraph Test")
    print("=" * 30)
    
    # Check if server is running
    if not test_health_check():
        print("❌ Please start the LangGraph server first:")
        print("   source venv/bin/activate && python langgraph_server.py")
        exit(1)
    
    # Run interactive conversation
    interactive_conversation() 