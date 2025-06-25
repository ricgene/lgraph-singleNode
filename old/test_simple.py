#!/usr/bin/env python3
"""
Simple Test Script for LangGraph Email Integration
This script tests the system to ensure it's working correctly.
"""

import requests
import json
import time

def test_system():
    """Test the system with a simple conversation"""
    print("🧪 Testing LangGraph Email Integration System")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n📋 Test 1: Health Check")
    print("-" * 30)
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Flask server is healthy")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Flask server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Flask server: {e}")
        return False
    
    # Test 2: Start conversation
    print("\n📝 Test 2: Start Conversation")
    print("-" * 30)
    try:
        start_data = {
            "user_email": "test@example.com"
        }
        response = requests.post("http://localhost:8000/start_conversation", json=start_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Conversation started successfully")
            print(f"Question: {result.get('question', 'No question')}")
            print(f"Is complete: {result.get('is_complete', False)}")
            conversation_history = result.get('conversation_history', '')
            print(f"Conversation history length: {len(conversation_history)}")
        else:
            print(f"❌ Failed to start conversation: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error starting conversation: {e}")
        return False
    
    # Test 3: Process a response
    print("\n💬 Test 3: Process Response")
    print("-" * 30)
    try:
        process_data = {
            "user_input": "Yes, I am ready to discuss my task",
            "user_email": "test@example.com"
        }
        response = requests.post("http://localhost:8000/process_message", json=process_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Response processed successfully")
            print(f"Question: {result.get('question', 'No question')}")
            print(f"Is complete: {result.get('is_complete', False)}")
            print(f"Completion state: {result.get('completion_state', 'Unknown')}")
        else:
            print(f"❌ Failed to process response: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error processing response: {e}")
        return False
    
    print("\n✅ All tests passed! System is working correctly.")
    return True

if __name__ == "__main__":
    test_system() 