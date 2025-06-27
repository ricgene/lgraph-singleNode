#!/usr/bin/env python3
"""
Local LangGraph test - no server needed
Pure local testing with mocks for momentum
Based on your paste.txt but simplified for local dev
"""

import json
import datetime
import os

# Test configuration - set these flags
TEST_MODE = True
LLM_PROVIDER = "mock" if TEST_MODE else "openai"
USE_FIRESTORE = False  # Start with dict, switch to True later

# Mock conversation state (instead of Firestore)
conversation_state = {}

# Log file
LOG_FILE = f"conversation_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

def mock_llm_response(user_input, turn_num):
    """Mock LLM responses for testing"""
    mock_responses = {
        1: "Hello! I'm here to help you with your task. What would you like to work on?",
        2: "That's interesting. Can you tell me more details about that?",
        3: "I understand. What's the most important aspect you'd like to focus on?",
        4: "Great! Let me help you with that. Is there anything specific you're concerned about?",
        5: "Perfect! I think we've covered everything. Let me summarize what we discussed."
    }
    return mock_responses.get(turn_num, f"Mock response {turn_num} to: {user_input}")

def run_langgraph_local(payload, turn_num):
    """
    Simulate your actual LangGraph logic locally
    Replace this with your real agent logic when ready
    """
    user_input = payload.get('user_input', '')
    previous_state = payload.get('previous_state', {})
    user_email = payload.get('user_email', previous_state.get('user_email', 'test@example.com'))
    
    # Get conversation history
    conversation_history = previous_state.get('conversation_history', '')
    
    # Mock LLM call (replace with your real agent logic)
    if TEST_MODE:
        agent_response = mock_llm_response(user_input, turn_num)
    else:
        # Your real LangGraph agent logic here
        agent_response = "Real agent response would go here"
    
    # Update conversation history
    new_conversation_history = conversation_history + f"\nUser: {user_input}\nAgent: {agent_response}"
    
    # Determine if complete (simple rule for testing)
    is_complete = turn_num >= 5 or "bye" in user_input.lower()
    
    # Build result (matching your oneNodeRemMem structure)
    result = {
        "question": agent_response,
        "is_complete": is_complete,
        "completion_state": "complete" if is_complete else "in_progress",
        "user_email": user_email,
        "conversation_history": new_conversation_history.strip(),
        "turn_number": turn_num
    }
    
    # Store state (dict for now, Firestore later)
    if USE_FIRESTORE:
        # TODO: Add Firestore save here
        pass
    else:
        conversation_state[user_email] = {
            'conversation_history': new_conversation_history,
            'turn_count': turn_num,
            'is_complete': is_complete
        }
    
    return result

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
    """Print detailed result information"""
    print(f"\n📊 Turn {turn_num} Result Details:")
    print("=" * 60)
    print(f"🤖 Question: {result.get('question', 'No question')}")
    print(f"✅ Is Complete: {result.get('is_complete', False)}")
    print(f"🎯 Completion State: {result.get('completion_state', 'Not set')}")
    print(f"📧 User Email: {result.get('user_email', 'Not set')}")
    
    # Show conversation history
    history = result.get('conversation_history', '')
    if history:
        print(f"\n📜 Conversation History:")
        print("-" * 40)
        print(history)
        print("-" * 40)
    
    # Log output to file
    log_to_file(result, turn_num, "output")

def main():
    print("🚀 LOCAL LangGraph Test - No Server Needed!")
    print("=" * 60)
    print(f"🧪 TEST_MODE: {TEST_MODE}")
    print(f"🤖 LLM_PROVIDER: {LLM_PROVIDER}")
    print(f"💾 USE_FIRESTORE: {USE_FIRESTORE}")
    print(f"📝 Logging to: {LOG_FILE}")
    
    # Initialize log file
    with open(LOG_FILE, "w") as f:
        f.write("")  # Clear file
    
    # Quick start option
    print("\n🚀 Quick start with default inputs? (y/n)")
    quick_start = input().strip().lower()
    
    if quick_start == 'y':
        # Pre-defined test conversation
        initial_payload = {
            "user_input": "Hello, I need help with my project",
            "previous_state": None,
            "user_email": "test@example.com"
        }
        
        test_inputs = [
            "I'm working on a Python application",
            "I need help with the architecture",
            "What about database design?",
            "Thanks for the help!"
        ]
    else:
        # Manual input
        print("\n📋 Enter initial input (or press Enter for default):")
        user_input = input("User message: ").strip()
        if not user_input:
            user_input = "Hello, I need help"
        
        email = input("Email (or press Enter for test@example.com): ").strip()
        if not email:
            email = "test@example.com"
        
        initial_payload = {
            "user_input": user_input,
            "previous_state": None,
            "user_email": email
        }
        
        test_inputs = []  # Will prompt for each turn
    
    print(f"\n✅ Starting conversation with:")
    print(f"   📧 Email: {initial_payload['user_email']}")
    print(f"   💬 Input: {initial_payload['user_input']}")
    
    # Log initial input
    log_to_file(initial_payload, 1, "input")
    
    # Process initial message
    print("\n🔄 Processing turn 1...")
    result = run_langgraph_local(initial_payload, 1)
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
        if quick_start == 'y' and len(test_inputs) >= turn_count - 1:
            user_input = test_inputs[turn_count - 2]
            print(f"👤 [Auto] Your response: {user_input}")
        else:
            user_input = input("👤 Your response: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'stop']:
            print("👋 Conversation ended.")
            break
        
        # Update payload for next turn
        next_payload = {
            "user_input": user_input,
            "previous_state": previous_state,
            "user_email": initial_payload['user_email']
        }
        
        # Log input to file
        log_to_file(next_payload, turn_count, "input")
        
        print("🔄 Processing...")
        result = run_langgraph_local(next_payload, turn_count)
        print_result_details(result, turn_count)
        
        # Update state
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
    print(f"\n💡 Next steps:")
    print(f"   1. Set USE_FIRESTORE = True to test with real Firestore")
    print(f"   2. Set TEST_MODE = False to test with real LLM")
    print(f"   3. Replace run_langgraph_local() with your real agent logic")

if __name__ == "__main__":
    main()