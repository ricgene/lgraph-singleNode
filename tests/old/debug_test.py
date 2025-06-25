#!/usr/bin/env python3
"""
Simple Debug Test Script for LangGraph Email Integration
This script tests the core conversation logic without the complexity of Flask server and email watcher.
"""

import json
import os
from oneNodeRemMem import process_message

def test_conversation_flow():
    """Test the conversation flow step by step"""
    print("🧪 Starting Debug Test for LangGraph Email Integration")
    print("=" * 60)
    
    # Test 1: Initial conversation start
    print("\n📝 Test 1: Starting new conversation")
    print("-" * 40)
    
    initial_input = {
        "user_input": "",
        "previous_state": None,
        "user_email": "test@example.com"
    }
    
    result = process_message(initial_input)
    print(f"✅ Initial response: {result['question']}")
    print(f"📧 Email sent: {result.get('user_email', 'No email')}")
    print(f"🔄 Is complete: {result['is_complete']}")
    
    # Test 2: First user response
    print("\n📝 Test 2: First user response")
    print("-" * 40)
    
    first_response = {
        "user_input": "Yes, I will call the contractor about my kitchen task",
        "previous_state": {
            "conversation_history": result["conversation_history"],
            "is_complete": result["is_complete"],
            "user_email": result["user_email"]
        },
        "user_email": result["user_email"]
    }
    
    result = process_message(first_response)
    print(f"✅ Second response: {result['question']}")
    print(f"📊 State: {result['is_complete']}")
    
    # Test 3: Second user response
    print("\n📝 Test 3: Second user response")
    print("-" * 40)
    
    second_response = {
        "user_input": "Yes, I'm ready to discuss the details",
        "previous_state": {
            "conversation_history": result["conversation_history"],
            "is_complete": result["is_complete"],
            "user_email": result["user_email"]
        },
        "user_email": result["user_email"]
    }
    
    result = process_message(second_response)
    print(f"✅ Third response: {result['question']}")
    print(f"📊 State: {result['is_complete']}")
    
    # Test 4: Third user response
    print("\n📝 Test 4: Third user response")
    print("-" * 40)
    
    third_response = {
        "user_input": "I will contact the contractor myself",
        "previous_state": {
            "conversation_history": result["conversation_history"],
            "is_complete": result["is_complete"],
            "user_email": result["user_email"]
        },
        "user_email": result["user_email"]
    }
    
    result = process_message(third_response)
    print(f"✅ Fourth response: {result['question']}")
    print(f"📊 State: {result['is_complete']}")
    
    # Test 5: Final user response
    print("\n📝 Test 5: Final user response")
    print("-" * 40)
    
    final_response = {
        "user_input": "No, I don't have any concerns",
        "previous_state": {
            "conversation_history": result["conversation_history"],
            "is_complete": result["is_complete"],
            "user_email": result["user_email"]
        },
        "user_email": result["user_email"]
    }
    
    result = process_message(final_response)
    print(f"✅ Final response: {result['question']}")
    print(f"📊 State: {result['is_complete']}")
    print(f"🏁 Completion state: {result['completion_state']}")
    
    # Print full conversation history
    print("\n📚 Full Conversation History:")
    print("-" * 40)
    print(result["conversation_history"])
    
    print("\n✅ Debug test completed!")

def test_duplicate_detection():
    """Test duplicate detection logic"""
    print("\n🔍 Testing Duplicate Detection")
    print("=" * 40)
    
    # Simulate the same email being processed multiple times
    initial_input = {
        "user_input": "Test response",
        "previous_state": None,
        "user_email": "test@example.com"
    }
    
    result1 = process_message(initial_input)
    print(f"First processing: {result1['question'][:50]}...")
    
    # Simulate duplicate processing
    result2 = process_message(initial_input)
    print(f"Duplicate processing: {result2['question'][:50]}...")
    
    print("✅ Duplicate detection test completed!")

if __name__ == "__main__":
    # Set up environment variables for testing
    # Note: In production, these should be set via environment variables
    os.environ["EMAIL_FUNCTION_URL"] = "https://sendemail-cs64iuly6q-uc.a.run.app"
    
    test_conversation_flow()
    test_duplicate_detection() 