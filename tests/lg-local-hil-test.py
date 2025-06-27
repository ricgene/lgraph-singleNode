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
from pathlib import Path

# Get the parent directory
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

MAX_TURNS = 7
TEST_MODE = True
VERBOSE = True
#AGENT_PROMPT_TYPE = "prizm"

# Import your actual agent
try:
    # Adjust this import path to match your agent file location
    from neNodeRemMem import process_message  # Change 'your_agent_file' to actual filename
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
TEST_MODE = True

# Test user and task info
TEST_USER_FIRST_NAME = "TestUser"
TEST_TASK_NAME = "Kitchen Renovation"

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
        "user_first_name": TEST_USER_FIRST_NAME,
        "task_name": TEST_TASK_NAME,
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
            "user_first_name": TEST_USER_FIRST_NAME,
            "task_name": TEST_TASK_NAME,
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
    if VERBOSE:
        print(f"\n🔍 VERBOSE: Input to agent (Turn {turn_num}):")
        print("=" * 60)
        print(f"📤 User Input: '{payload.get('user_input', '')}'")
        print(f"👤 User First Name: '{payload.get('user_first_name', '')}'")
        print(f"📋 Task Name: '{payload.get('task_name', '')}'")
        print(f"📋 Previous State: {json.dumps(payload.get('previous_state', None), indent=2)}")
        print("=" * 60)
    
    if AGENT_AVAILABLE and not TEST_MODE:
        # Use your real agent (async)
        try:
            result = await process_message(payload)
            return result
        except Exception as e:
            print(f"❌ Error running real agent: {e}")
            # Fall back to mock (synchronous)
            return run_mock_agent(payload, turn_num)
    else:
        # Use mock agent (synchronous)
        return run_mock_agent(payload, turn_num)

def run_mock_agent(payload, turn_num):
    """
    Mock agent that simulates your agent's behavior for testing
    This is synchronous to keep things simple
    """
    user_input = payload.get('user_input', '')
    user_first_name = payload.get('user_first_name', 'User')
    task_name = payload.get('task_name', 'Task')
    previous_state = payload.get('previous_state', None)
    
    if VERBOSE:
        print(f"\n🤖 VERBOSE: Mock agent processing (Turn {turn_num}):")
        print(f"📝 User input: '{user_input}'")
        print(f"👤 User first name: '{user_first_name}'")
        print(f"📋 Task name: '{task_name}'")
        print(f"📊 Previous state keys: {list(previous_state.keys()) if previous_state else 'None'}")
    
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
    
    if VERBOSE:
        print(f"🔄 Turn count: {turn_count}")
        print(f"📜 Conversation history length: {len(conversation_history)} chars")
    
    # Mock responses based on prompt type and turn
    if AGENT_PROMPT_TYPE == "debug":
        question = f"Debug question {turn_count} for {user_first_name} about {task_name}"
        learned = f"Debug learned: {user_input}"
        # Complete after 3 turns in debug mode
        is_complete = turn_count >= 3
        completion_state = "TASK_PROGRESSING" if is_complete else "OTHER"
    elif AGENT_PROMPT_TYPE == "generic":
        if turn_count == 1:
            question = f"Hello {user_first_name}, what can I help you with today regarding your {task_name}?"
            learned = "Starting conversation"
        else:
            question = f"Thanks for that response, {user_first_name}. Anything else about your {task_name}?"
            learned = f"User said: {user_input}"
        is_complete = turn_count >= 4
        completion_state = "TASK_COMPLETE" if is_complete else "OTHER"
    else:  # prizm mode
        if turn_count == 1:
            question = f"Hello {user_first_name}, are you ready to discuss the {task_name} you need assistance with?"
            learned = "No information has been provided yet."
        elif "yes" in user_input.lower() and "ready" in user_input.lower():
            question = f"Great {user_first_name}! Will you reach out to the contractor for your {task_name}?"
            learned = f"User is ready to discuss task."
        elif "yes" in user_input.lower() and "contractor" in user_input.lower():
            question = f"Perfect {user_first_name}! Do you have any concerns or questions about your {task_name}?"
            learned = f"User will contact contractor."
        elif "no" in user_input.lower() and ("concern" in user_input.lower() or "question" in user_input.lower()):
            question = f"Thank you for selecting Prizm, {user_first_name}! Have a great rest of your day! TASK_PROGRESSING"
            learned = f"User has no concerns."
            is_complete = True
            completion_state = "TASK_PROGRESSING"
        else:
            question = f"I see, {user_first_name}. Can you tell me more about your {task_name}?"
            learned = f"User response: {user_input}"
            is_complete = False
            completion_state = "OTHER"
    
    # Default completion logic
    if 'is_complete' not in locals():
        is_complete = turn_count >= MAX_TURNS
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
    
    if VERBOSE:
        print(f"🤖 Generated question: '{question}'")
        print(f"📚 Learned: '{learned}'")
        print(f"✅ Is complete: {is_complete}")
        print(f"🎯 Completion state: {completion_state}")
    
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
    
    if VERBOSE:
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
            "user_first_name": TEST_USER_FIRST_NAME,
            "task_name": TEST_TASK_NAME,
            "previous_state": None
        }
        
        test_inputs = [
            "Yes, I'm ready to discuss my task",
            "I need help with kitchen renovation", 
            "Yes, I'll reach out to the contractor",
            "No concerns, thanks!",
            "Everything looks good",
            "Let's proceed",
            "I'm ready to move forward"
        ]
    else:
        # Manual input
        print("\n📋 Initial input (leave empty for greeting, or enter message):")
        user_input = input("User message: ").strip()
        
        initial_payload = {
            "user_input": user_input,
            "user_first_name": TEST_USER_FIRST_NAME,
            "task_name": TEST_TASK_NAME,
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
    result = asyncio.run(run_langgraph_local(initial_payload, 1))
    print_result_details(result, 1)
    
    # Conversation loop
    turn_count = 1
    previous_state = {
        'conversation_history': result.get('conversation_history', ''),
        'all_info_collected': False,
        'user_email': result.get('user_email', 'test@example.com')
    }
    
    while not result.get('is_complete', False) and turn_count < MAX_TURNS:
        turn_count += 1
        print(f"\n🔄 Turn {turn_count}/{MAX_TURNS}")
        print("-" * 20)
        
        # Get user response
        if quick_start == 'y' and turn_count - 2 < len(test_inputs):
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
            "user_first_name": TEST_USER_FIRST_NAME,
            "task_name": TEST_TASK_NAME,
            "previous_state": previous_state
        }
        
        if VERBOSE:
            print(f"\n📦 VERBOSE: Constructing payload for turn {turn_count}:")
            print(f"   📤 User input: '{user_input}'")
            print(f"   📋 Previous state keys: {list(previous_state.keys())}")
            print(f"   📜 History length: {len(previous_state.get('conversation_history', ''))} chars")
        
        # Log input to file
        log_to_file(next_payload, turn_count, "input")
        
        print("🔄 Processing...")
        result = asyncio.run(run_langgraph_local(next_payload, turn_count))
        print_result_details(result, turn_count)
        
        # Update state (matching your agent's state structure)
        previous_state = {
            'conversation_history': result.get('conversation_history', ''),
            'all_info_collected': False,
            'user_email': result.get('user_email', 'test@example.com')
        }
        
        if VERBOSE:
            print(f"\n📊 VERBOSE: Updated state after turn {turn_count}:")
            print(f"   📜 New history length: {len(previous_state['conversation_history'])} chars")
            print(f"   ✅ Is complete: {result.get('is_complete', False)}")
            print(f"   🎯 Completion state: {result.get('completion_state', 'Unknown')}")
    
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