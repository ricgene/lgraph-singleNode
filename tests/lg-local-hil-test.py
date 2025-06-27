#!/usr/bin/env python3
"""
Local LangGraph test - import and test actual agent with mock scenarios
Pure local testing with mocks for momentum
"""

import json
import datetime
import os
import asyncio
import sys

# Import your actual agent
try:
    # Adjust this import path to match your agent file location
    from ../oneNodeRemMem import process_message  # Change 'your_agent_file' to actual filename
    AGENT_AVAILABLE = True
    print("✅ Successfully imported actual agent")
except ImportError as e:
    print(f"⚠️ Could not import agent: {e}")
    print("   Will use mock agent instead")
    AGENT_AVAILABLE = False

# Test configuration - set these flags
TEST_MODE = True
LLM_PROVIDER = "mock" if TEST_MODE else "openai"
USE_FIRESTORE = False  # Start with dict, switch to True later
AGENT_PROMPT_TYPE = os.getenv("AGENT_PROMPT_TYPE", "debug")  # debug, generic, prizm

# Test scenarios - easy to select and run
TEST_SCENARIOS = {
    "happy_path": {
        "description": "User cooperates and completes task",
        "inputs": [
            "",  # Initial greeting
            "Yes, I'm ready to discuss my task",
            "Yes, I'll reach out to the contractor",
            "No concerns, let's proceed"
        ],
        "expected_completion": "TASK_PROGRESSING"
    },
    
    "escalation": {
        "description": "User has concerns and needs escalation", 
        "inputs": [
            "",
            "I'm ready to discuss",
            "I'm not sure about the contractor",
            "I have many concerns about this approach"
        ],
        "expected_completion": "TASK_ESCALATION"
    },
    
    "unclear_responses": {
        "description": "User gives unclear responses",
        "inputs": [
            "",
            "Maybe",
            "I don't know",
            "What do you think?",
            "Sure, whatever"
        ],
        "expected_completion": "OTHER"
    },
    
    "max_turns": {
        "description": "Conversation hits turn limit",
        "inputs": [
            "",
            "Tell me more",
            "Keep going", 
            "What else?",
            "More info please",
            "Continue",
            "And then?"
        ],
        "expected_completion": "OTHER"
    },
    
    "debug_simple": {
        "description": "Simple test for debug mode",
        "inputs": [
            "",
            "Hello",
            "Yes", 
            "Okay"
        ],
        "expected_completion": "TASK_PROGRESSING"
    }
}

# Mock conversation state (instead of Firestore)
conversation_state = {}

# Log file
LOG_FILE = f"conversation_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

async def run_scenario(scenario_name, scenario_data):
    """Run a specific test scenario"""
    print(f"\n🎯 Running scenario: {scenario_name}")
    print(f"📝 Description: {scenario_data['description']}")
    print(f"📊 Expected completion: {scenario_data['expected_completion']}")
    print("=" * 60)
    
    inputs = scenario_data['inputs']
    expected_completion = scenario_data['expected_completion']
    
    # Initial payload
    initial_payload = {
        "user_input": inputs[0],
        "previous_state": None
    }
    
    # Log scenario start
    log_to_file({
        "scenario": scenario_name, 
        "description": scenario_data['description'],
        "expected": expected_completion
    }, 0, "scenario_start")
    
    # Process first turn
    result = await run_langgraph_local(initial_payload, 1)
    print_result_details(result, 1)
    
    # Continue with remaining inputs
    previous_state = {
        'conversation_history': result.get('conversation_history', ''),
        'is_complete': result.get('is_complete', False),
        'turn_count': result.get('turn_count', 1),
        'user_email': result.get('user_email', 'test@example.com')
    }
    
    turn_count = 1
    for i, user_input in enumerate(inputs[1:], 2):
        if result.get('is_complete', False):
            print(f"\n✅ Conversation completed early at turn {turn_count}")
            break
            
        turn_count = i
        print(f"\n🔄 Turn {turn_count}: User says '{user_input}'")
        
        next_payload = {
            "user_input": user_input,
            "previous_state": previous_state
        }
        
        log_to_file(next_payload, turn_count, "input")
        result = await run_langgraph_local(next_payload, turn_count)
        print_result_details(result, turn_count)
        
        # Update state
        previous_state = {
            'conversation_history': result.get('conversation_history', ''),
            'is_complete': result.get('is_complete', False),
            'turn_count': result.get('turn_count', turn_count),
            'user_email': result.get('user_email', 'test@example.com')
        }
    
    # Check results
    actual_completion = result.get('completion_state', 'OTHER')
    success = actual_completion == expected_completion
    
    print(f"\n🏁 Scenario complete!")
    print(f"   Expected: {expected_completion}")
    print(f"   Actual:   {actual_completion}")
    print(f"   Result:   {'✅ PASS' if success else '❌ FAIL'}")
    print(f"   Turns:    {result.get('turn_count', 0)}")
    
    return {
        'scenario': scenario_name,
        'success': success,
        'expected': expected_completion,
        'actual': actual_completion,
        'turns': result.get('turn_count', 0)
    }

async def run_multiple_scenarios(scenario_names=None):
    """Run multiple scenarios and summarize results"""
    if scenario_names is None:
        scenario_names = list(TEST_SCENARIOS.keys())
    
    results = []
    
    for scenario_name in scenario_names:
        if scenario_name not in TEST_SCENARIOS:
            print(f"⚠️ Unknown scenario: {scenario_name}")
            continue
            
        result = await run_scenario(scenario_name, TEST_SCENARIOS[scenario_name])
        results.append(result)
        
        print("\n" + "="*60)
    
    # Summary
    print(f"\n📊 SUMMARY - Ran {len(results)} scenarios:")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"   {status} {result['scenario']} ({result['turns']} turns)")
    
    print(f"\n🏆 Overall: {passed}/{len(results)} passed ({failed} failed)")
    
    return results

async def run_langgraph_local(payload, turn_num):
    """
    Run your actual agent or mock it based on TEST_MODE
    """
    if AGENT_AVAILABLE and not TEST_MODE:
        # Use your real agent
        try:
            result = await process_message(payload)
            return result
        except Exception as e:
            print(f"❌ Error running real agent: {e}")
            # Fall back to mock
            return run_mock_agent(payload, turn_num)
    else:
        # Use mock agent
        return run_mock_agent(payload, turn_num)

def run_mock_agent(payload, turn_num):
    """
    Mock agent that simulates your agent's behavior for testing
    """
    user_input = payload.get('user_input', '')
    previous_state = payload.get('previous_state', None)
    
    # Initialize state like your agent does
    if previous_state is None:
        conversation_history = ""
        user_email = "test@example.com"
        turn_count = 0
    else:
        conversation_history = previous_state.get('conversation_history', '')
        user_email = previous_state.get('user_email', 'test@example.com')
        turn_count = previous_state.get('turn_count', 0)
    
    # Increment turn count
    turn_count += 1
    
    # Mock responses based on prompt type and turn
    if AGENT_PROMPT_TYPE == "debug":
        question = f"Debug question {turn_count}"
        learned = f"Debug learned: {user_input}"
        # Complete after 3 turns in debug mode
        is_complete = turn_count >= 3
        completion_state = "TASK_PROGRESSING" if is_complete else "OTHER"
    elif AGENT_PROMPT_TYPE == "generic":
        if turn_count == 1:
            question = "What can I help you with today?"
            learned = "Starting conversation"
        else:
            question = f"Thanks for that response. Anything else?"
            learned = f"User said: {user_input}"
        is_complete = turn_count >= 4
        completion_state = "TASK_COMPLETE" if is_complete else "OTHER"
    else:  # prizm mode
        if turn_count == 1:
            question = "Hello, are you ready to discuss the home task you need assistance with?"
            learned = "No information has been provided yet."
        elif "yes" in user_input.lower() and "ready" in user_input.lower():
            question = "Great! Will you reach out to the contractor?"
            learned = f"User is ready to discuss task."
        elif "yes" in user_input.lower() and "contractor" in user_input.lower():
            question = "Perfect! Do you have any concerns or questions about this task?"
            learned = f"User will contact contractor."
        elif "no" in user_input.lower() and ("concern" in user_input.lower() or "question" in user_input.lower()):
            question = "Thank you for selecting Prizm, have a great rest of your day! TASK_PROGRESSING"
            learned = f"User has no concerns."
            is_complete = True
            completion_state = "TASK_PROGRESSING"
        else:
            question = f"I see. Can you tell me more about that?"
            learned = f"User response: {user_input}"
            is_complete = False
            completion_state = "OTHER"
    
    # Default completion logic
    if 'is_complete' not in locals():
        is_complete = turn_count >= 7
        completion_state = "OTHER"
    
    # Update conversation history
    if question:
        conversation_history += f"\nQuestion: {question}"
    if learned:
        conversation_history += f"\nLearned: {learned}"
    
    # Check for completion keywords in history
    if "TASK_PROGRESSING" in conversation_history:
        is_complete = True
        completion_state = "TASK_PROGRESSING"
    elif "TASK_ESCALATION" in conversation_history:
        is_complete = True
        completion_state = "TASK_ESCALATION"
    
    return {
        "question": question if not is_complete else "",
        "conversation_history": conversation_history.strip(),
        "is_complete": is_complete,
        "completion_state": completion_state,
        "user_email": user_email,
        "turn_count": turn_count
    }

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
        # Pre-defined test conversation matching your agent's expected flow
        initial_payload = {
            "user_input": "",  # Empty for initial greeting
            "previous_state": None
        }
        
        test_inputs = [
            "Yes, I'm ready to discuss my task",
            "I need help with kitchen renovation", 
            "Yes, I'll reach out to the contractor",
            "No concerns, thanks!"
        ]
    else:
        # Manual input
        print("\n📋 Initial input (leave empty for greeting, or enter message):")
        user_input = input("User message: ").strip()
        
        initial_payload = {
            "user_input": user_input,
            "previous_state": None
        }
        
        test_inputs = []  # Will prompt for each turn
    
    print(f"\n✅ Starting conversation:")
    print(f"   💬 Initial Input: '{initial_payload['user_input']}'")
    print(f"   📋 Previous State: {initial_payload['previous_state']}")
    
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
        'user_email': result.get('user_email', 'test@example.com')
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
        
        # Update payload for next turn (matching your agent's expected format)
        next_payload = {
            "user_input": user_input,
            "previous_state": previous_state
        }
        
        # Log input to file
        log_to_file(next_payload, turn_count, "input")
        
        print("🔄 Processing...")
        result = run_langgraph_local(next_payload, turn_count)
        print_result_details(result, turn_count)
        
        # Update state (matching your agent's state structure)
        previous_state = {
            'conversation_history': result.get('conversation_history', ''),
            'all_info_collected': False,
            'user_email': result.get('user_email', 'test@example.com')
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