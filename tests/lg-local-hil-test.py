#!/usr/bin/env python3
"""
Real-time test script - paste your input structure and responses
"""

import requests
import json

# Server URL
SERVER_URL = "http://localhost:8000"

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

def main():
    print("🚀 Real-time LangGraph Test")
    print("=" * 30)
    
    # Check server health
    try:
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print("❌ Server not responding")
            return
    except:
        print("❌ Cannot connect to server")
        return
    
    print("\n📋 Paste your initial input structure (JSON):")
    print("(Press Enter twice when done)")
    
    # Get initial input structure
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    
    initial_payload = json.loads("\n".join(lines))
    
    print(f"\n✅ Initial payload received:")
    print(f"   📋 Task: {initial_payload['task_json']['taskTitle']}")
    print(f"   📧 Email: {initial_payload['user_email']}")
    print(f"   💬 Input: {initial_payload['user_input']}")
    
    # Send initial message
    print("\n🔄 Sending to agent...")
    result = send_message(initial_payload)
    
    if not result:
        print("❌ Failed to get response")
        return
    
    print(f"✅ Agent Response:")
    print(f"🤖 {result.get('question', 'No response')}")
    print(f"📊 Complete: {result.get('is_complete', False)}")
    
    # Conversation loop
    turn_count = 1
    previous_state = {
        'conversation_history': result.get('conversation_history', ''),
        'is_complete': result.get('is_complete', False),
        'user_email': initial_payload['user_email']
    }
    
    while not result.get('is_complete', False) and turn_count < 7:
        turn_count += 1
        print(f"\n🔄 Turn {turn_count}/7")
        print("-" * 20)
        
        # Get user response
        user_input = input("👤 Your response: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'stop']:
            print("👋 Conversation ended.")
            break
        
        # Update payload for next turn
        next_payload = {
            "user_input": user_input,
            "user_email": initial_payload['user_email'],
            "task_json": initial_payload['task_json'],
            "previous_state": previous_state
        }
        
        print("🔄 Sending to agent...")
        result = send_message(next_payload)
        
        if not result:
            print("❌ Failed to get response")
            break
        
        print(f"✅ Agent Response:")
        print(f"🤖 {result.get('question', 'No response')}")
        print(f"📊 Complete: {result.get('is_complete', False)}")
        
        # Update state
        previous_state = {
            'conversation_history': result.get('conversation_history', ''),
            'is_complete': result.get('is_complete', False),
            'user_email': initial_payload['user_email']
        }
    
    if result.get('is_complete', False):
        print("\n🏁 Conversation completed!")
    else:
        print("\n⏰ Maximum turns reached.")
    
    print(f"📊 Total turns: {turn_count}")

if __name__ == "__main__":
    main() 