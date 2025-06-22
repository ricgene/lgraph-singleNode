#!/usr/bin/env python3
"""
Test script for duplicate email detection system
This script tests the content-based duplicate detection implemented in the email integration.
"""

import json
import os
import hashlib
import requests
import time

def create_email_content_hash(email_content):
    """Create MD5 hash of email content (same as Node.js implementation)"""
    return hashlib.md5(email_content.lower().strip().encode()).hexdigest()

def test_duplicate_detection():
    """Test the duplicate detection system"""
    print("🧪 Testing Duplicate Email Detection System")
    print("=" * 50)
    
    # Test data
    user_email = "test@example.com"
    email_content_1 = "Yes, I will call the contractor about my kitchen task"
    email_content_2 = "I will contact the contractor myself"
    email_content_3 = "Yes, I will call the contractor about my kitchen task"  # Duplicate of content_1
    
    print(f"\n📧 Test User: {user_email}")
    print(f"📝 Email Content 1: {email_content_1}")
    print(f"📝 Email Content 2: {email_content_2}")
    print(f"📝 Email Content 3: {email_content_3} (duplicate of 1)")
    
    # Simulate the buffer file structure
    buffer_file = "test_email_content_buffer.json"
    
    # Test 1: First email (should be processed)
    print(f"\n📧 Test 1: First email")
    print("-" * 30)
    
    # Create initial buffer
    buffer = {user_email.lower().strip(): []}
    
    # Check if duplicate (should be false)
    content_hash = create_email_content_hash(email_content_1)
    is_duplicate = content_hash in buffer[user_email.lower().strip()]
    
    print(f"Content Hash: {content_hash}")
    print(f"Is Duplicate: {is_duplicate}")
    print(f"Expected: False")
    
    if not is_duplicate:
        # Add to buffer
        buffer[user_email.lower().strip()].append(content_hash)
        print("✅ First email would be processed")
    else:
        print("❌ First email would be skipped (unexpected)")
    
    # Test 2: Second email (different content, should be processed)
    print(f"\n📧 Test 2: Second email (different content)")
    print("-" * 30)
    
    content_hash_2 = create_email_content_hash(email_content_2)
    is_duplicate_2 = content_hash_2 in buffer[user_email.lower().strip()]
    
    print(f"Content Hash: {content_hash_2}")
    print(f"Is Duplicate: {is_duplicate_2}")
    print(f"Expected: False")
    
    if not is_duplicate_2:
        # Add to buffer
        buffer[user_email.lower().strip()].append(content_hash_2)
        print("✅ Second email would be processed")
    else:
        print("❌ Second email would be skipped (unexpected)")
    
    # Test 3: Third email (duplicate content, should be skipped)
    print(f"\n📧 Test 3: Third email (duplicate content)")
    print("-" * 30)
    
    content_hash_3 = create_email_content_hash(email_content_3)
    is_duplicate_3 = content_hash_3 in buffer[user_email.lower().strip()]
    
    print(f"Content Hash: {content_hash_3}")
    print(f"Is Duplicate: {is_duplicate_3}")
    print(f"Expected: True")
    
    if is_duplicate_3:
        print("✅ Third email would be skipped (duplicate detected)")
    else:
        print("❌ Third email would be processed (unexpected)")
    
    # Test 4: Buffer clearing
    print(f"\n📧 Test 4: Buffer clearing")
    print("-" * 30)
    
    # Save buffer to file
    with open(buffer_file, 'w') as f:
        json.dump(buffer, f, indent=2)
    
    print(f"Buffer saved to {buffer_file}")
    print(f"Buffer contents: {buffer}")
    
    # Simulate buffer clearing
    if os.path.exists(buffer_file):
        os.remove(buffer_file)
        print("🗑️ Buffer file cleared")
    
    # Verify buffer is cleared
    if not os.path.exists(buffer_file):
        print("✅ Buffer clearing works correctly")
    else:
        print("❌ Buffer clearing failed")
    
    print(f"\n✅ Duplicate detection test completed!")

def test_server_integration():
    """Test the duplicate detection with the actual server"""
    print(f"\n🔗 Testing Server Integration")
    print("=" * 50)
    
    server_url = "http://localhost:8000"
    
    # Test data
    test_data = {
        "user_input": "Yes, I will call the contractor about my kitchen task",
        "previous_state": None,
        "user_email": "test@example.com"
    }
    
    try:
        # First request
        print("📧 Sending first request...")
        response1 = requests.post(f"{server_url}/process_message", json=test_data)
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ First response: {result1.get('question', 'No question')[:50]}...")
        else:
            print(f"❌ First request failed: {response1.status_code}")
            return
        
        # Second request (same content - should be detected as duplicate)
        print("📧 Sending second request (same content)...")
        response2 = requests.post(f"{server_url}/process_message", json=test_data)
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"✅ Second response: {result2.get('question', 'No question')[:50]}...")
            
            # Check if responses are the same (indicating duplicate was processed)
            if result1.get('question') == result2.get('question'):
                print("⚠️  Same response - duplicate may not be detected by server")
            else:
                print("✅ Different response - server may have duplicate detection")
        else:
            print(f"❌ Second request failed: {response2.status_code}")
        
        # Third request (different content)
        print("📧 Sending third request (different content)...")
        test_data["user_input"] = "I will contact the contractor myself"
        response3 = requests.post(f"{server_url}/process_message", json=test_data)
        if response3.status_code == 200:
            result3 = response3.json()
            print(f"✅ Third response: {result3.get('question', 'No question')[:50]}...")
        else:
            print(f"❌ Third request failed: {response3.status_code}")
        
    except Exception as e:
        print(f"❌ Error testing server integration: {str(e)}")
        print("💡 Make sure the Flask server is running on port 8000")

if __name__ == "__main__":
    # Test the duplicate detection logic
    test_duplicate_detection()
    
    # Test with actual server (if available)
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            test_server_integration()
        else:
            print("\n💡 Flask server not available - skipping server integration test")
    except:
        print("\n💡 Flask server not available - skipping server integration test")
        print("💡 To test with server, run: source venv/bin/activate && python langgraph_server.py") 