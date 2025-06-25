#!/usr/bin/env python3
"""
Real-time test script - paste your input structure and responses
Matches oneNodeRemMem.py structure exactly
Captures complete input/output stream to file
"""

import requests
import json
import datetime
import os

# Server URL
SERVER_URL = "http://localhost:8000"

# Log file
LOG_FILE = f"conversation_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

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

def log_to_file(data, turn_num, turn_type):
    """Log input/output data to file"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "turn_number": turn_num,
        "turn_type": turn_type,  # "input" or "output"
        "data": data
    }
    
    # Append to log file
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry, indent=2) + "\n")

def print_result_details(result, turn_num):
    """Print detailed result information from oneNodeRemMem.py"""
    print(f"\n📊 Turn {turn_num} Result Details:")
    print("=" * 60)
    print(f"🤖 Question: {result.get('question', 'No question')}")
    print(f"✅ Is Complete: {result.get('is_complete', False)}")
    print(f"🎯 Completion State: {result.get('completion_state', 'Not set')}")
    print(f"📧 User Email: {result.get('user_email', 'Not set')}")
    
    # Show complete conversation history
    history = result.get('conversation_history', '')
    if history:
        print(f"\n📜 COMPLETE Conversation History:")
        print("-" * 40)
        print(history)
        print("-" * 40)
    
    print(f"\n📋 COMPLETE Return Structure:")
    print(json.dumps(result, indent=2))
    print("=" * 60)
    
    # Log output to file
    log_to_file(result, turn_num, "output")

def main():
    print("🚀 Real-time LangGraph Test (oneNodeRemMem.py structure)")
    print("=" * 60)
    print(f"📝 Logging to: {LOG_FILE}")
    
    # Initialize log file
    with open(LOG_FILE, "w") as f:
        f.write("")  # Clear file
    
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
    print("Expected structure:")
    print('{\n  "user_input": "",\n  "previous_state": null,\n  "user_email": "your.email@example.com"\n}')
    print("\n(Press Enter twice when done)")
    
    # Get initial input structure
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    
    initial_payload = json.loads("\n".join(lines))
    
    print(f"\n✅ Initial payload received:")
    print(f"   📧 Email: {initial_payload['user_email']}")
    print(f"   💬 Input: {initial_payload['user_input']}")
    
    # Log initial input
    log_to_file(initial_payload, 1, "input")
    
    # Send initial message
    print("\n🔄 Sending to agent...")
    result = send_message(initial_payload)
    
    if not result:
        print("❌ Failed to get response")
        return
    
    # Show detailed result for turn 1
    print_result_details(result, 1)
    
    # Conversation loop
    turn_count = 1
    previous_state = {
        'conversation_history': result.get('conversation_history', ''),
        'all_info_collected': False,
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
        
        # Update payload for next turn (matching oneNodeRemMem.py structure)
        next_payload = {
            "user_input": user_input,
            "previous_state": previous_state
        }
        
        # Log input to file
        log_to_file(next_payload, turn_count, "input")
        
        print("🔄 Sending to agent...")
        result = send_message(next_payload)
        
        if not result:
            print("❌ Failed to get response")
            break
        
        # Show detailed result for this turn
        print_result_details(result, turn_count)
        
        # Update state (matching oneNodeRemMem.py structure)
        previous_state = {
            'conversation_history': result.get('conversation_history', ''),
            'all_info_collected': False,
            'user_email': initial_payload['user_email']
        }
    
    if result.get('is_complete', False):
        print("\n🏁 Conversation completed!")
        print(f"🎯 Final Completion State: {result.get('completion_state', 'Unknown')}")
    else:
        print("\n⏰ Maximum turns reached.")
    
    print(f"📊 Total turns: {turn_count}")
    print(f"📝 Complete log saved to: {LOG_FILE}")

if __name__ == "__main__":
    main() 