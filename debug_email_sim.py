#!/usr/bin/env python3
"""
Simple Email Processing Debug Script
This script simulates email processing without the complexity of IMAP connections.
"""

import json
import requests
import time

def simulate_email_processing():
    """Simulate email processing by directly calling the Flask server"""
    print("📧 Starting Email Processing Debug Test")
    print("=" * 50)
    
    # Flask server URL
    server_url = "http://localhost:8000"
    
    # Test 1: Start conversation
    print("\n📝 Test 1: Starting conversation")
    print("-" * 30)
    
    start_data = {
        "user_email": "test@example.com"
    }
    
    try:
        response = requests.post(f"{server_url}/start_conversation", json=start_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Conversation started: {result.get('question', 'No question')}")
        else:
            print(f"❌ Failed to start conversation: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error starting conversation: {str(e)}")
        return
    
    # Test 2: Process first email
    print("\n📝 Test 2: Processing first email")
    print("-" * 30)
    
    email1_data = {
        "user_input": "Yes, I will call the contractor about my kitchen task",
        "previous_state": result.get("previous_state"),
        "user_email": "test@example.com"
    }
    
    try:
        response = requests.post(f"{server_url}/process_message", json=email1_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ First email processed: {result.get('question', 'No question')}")
            print(f"📊 State: {result.get('is_complete', False)}")
        else:
            print(f"❌ Failed to process first email: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error processing first email: {str(e)}")
        return
    
    # Test 3: Process second email (simulate duplicate)
    print("\n📝 Test 3: Processing second email (same content)")
    print("-" * 30)
    
    email2_data = {
        "user_input": "Yes, I will call the contractor about my kitchen task",  # Same content
        "previous_state": result.get("previous_state"),
        "user_email": "test@example.com"
    }
    
    try:
        response = requests.post(f"{server_url}/process_message", json=email2_data)
        if response.status_code == 200:
            result2 = response.json()
            print(f"✅ Second email processed: {result2.get('question', 'No question')}")
            print(f"📊 State: {result2.get('is_complete', False)}")
            
            # Check if it's the same response (duplicate detection working)
            if result2.get('question') == result.get('question'):
                print("⚠️  Duplicate detected - same response")
            else:
                print("✅ Different response - duplicate detection may not be working")
        else:
            print(f"❌ Failed to process second email: {response.status_code}")
    except Exception as e:
        print(f"❌ Error processing second email: {str(e)}")
    
    # Test 4: Process third email (different content)
    print("\n📝 Test 4: Processing third email (different content)")
    print("-" * 30)
    
    email3_data = {
        "user_input": "I will contact the contractor myself",
        "previous_state": result.get("previous_state"),
        "user_email": "test@example.com"
    }
    
    try:
        response = requests.post(f"{server_url}/process_message", json=email3_data)
        if response.status_code == 200:
            result3 = response.json()
            print(f"✅ Third email processed: {result3.get('question', 'No question')}")
            print(f"📊 State: {result3.get('is_complete', False)}")
        else:
            print(f"❌ Failed to process third email: {response.status_code}")
    except Exception as e:
        print(f"❌ Error processing third email: {str(e)}")
    
    print("\n✅ Email processing debug test completed!")

def check_server_health():
    """Check if the Flask server is running"""
    print("🏥 Checking server health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy and running")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server - is it running?")
        return False
    except Exception as e:
        print(f"❌ Error checking server health: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 Email Processing Debug Tool")
    print("=" * 40)
    
    # Check server health first
    if not check_server_health():
        print("\n💡 To start the server, run:")
        print("   source venv/bin/activate && python langgraph_server.py")
        print("\n💡 Then run this debug script again.")
        exit(1)
    
    # Run the simulation
    simulate_email_processing() 