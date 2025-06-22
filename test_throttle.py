#!/usr/bin/env python3
"""
Test Email Throttling Functionality
This script demonstrates the email throttling system that prevents emails from being sent too quickly.
"""

import time
import requests
import json

def test_throttle_logic():
    """Test the throttle logic (simulated)"""
    print("🧪 Testing Email Throttle Logic")
    print("=" * 50)
    
    # Simulate the throttle logic from Node.js
    def throttle_email_sending(user_email, last_sent_time):
        now = int(time.time() * 1000)  # Current time in milliseconds
        time_since_last_email = now - last_sent_time
        min_interval = 3000  # 3 seconds minimum
        
        if time_since_last_email < min_interval:
            # Calculate wait time based on even/odd seconds
            current_seconds = int(now / 1000)
            is_even_second = current_seconds % 2 == 0
            wait_time = 1000 if is_even_second else 3000  # 1 second if even, 3 seconds if odd
            
            return wait_time, is_even_second
        return 0, None
    
    # Test scenarios
    test_cases = [
        {"user": "test@example.com", "last_sent": 0, "description": "First email (no throttle)"},
        {"user": "test@example.com", "last_sent": int(time.time() * 1000) - 1000, "description": "Email 1 second ago (should throttle)"},
        {"user": "test@example.com", "last_sent": int(time.time() * 1000) - 5000, "description": "Email 5 seconds ago (no throttle)"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📧 Test {i}: {test_case['description']}")
        print("-" * 40)
        
        wait_time, is_even = throttle_email_sending(test_case['user'], test_case['last_sent'])
        
        if wait_time > 0:
            print(f"⏰ Throttling: {wait_time}ms wait ({'even' if is_even else 'odd'} second)")
        else:
            print("✅ No throttling needed")
    
    print(f"\n✅ Throttle logic test completed!")

def test_server_throttle():
    """Test throttling with the actual server"""
    print(f"\n🔗 Testing Server Throttle Integration")
    print("=" * 50)
    print("⚠️  WARNING: This test will send actual emails to richard.genet@gmail.com")
    print("=" * 50)
    
    server_url = "http://localhost:8000"
    
    # Test data
    test_data = {
        "user_input": "Yes, I am ready to discuss my task",
        "previous_state": None,
        "user_email": "richard.genet@gmail.com"  # Use real email instead of test address
    }
    
    try:
        # First request
        print("📧 Sending first request...")
        start_time = time.time()
        response1 = requests.post(f"{server_url}/process_message", json=test_data)
        end_time = time.time()
        
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ First response: {result1.get('question', 'No question')[:50]}...")
            print(f"⏱️  Time taken: {(end_time - start_time):.2f}s")
        else:
            print(f"❌ First request failed: {response1.status_code}")
            return
        
        # Second request (should be throttled)
        print("\n📧 Sending second request (should be throttled)...")
        start_time = time.time()
        response2 = requests.post(f"{server_url}/process_message", json=test_data)
        end_time = time.time()
        
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"✅ Second response: {result2.get('question', 'No question')[:50]}...")
            print(f"⏱️  Time taken: {(end_time - start_time):.2f}s")
            
            # Check if responses are the same (indicating duplicate was processed)
            if result2.get('question') == result1.get('question'):
                print("⚠️  Same response - duplicate may not be detected by server")
            else:
                print("✅ Different response - server may have duplicate detection")
        else:
            print(f"❌ Second request failed: {response2.status_code}")
        
        # Third request (different content)
        print("\n📧 Sending third request (different content)...")
        test_data["user_input"] = "I have a different response this time"
        start_time = time.time()
        response3 = requests.post(f"{server_url}/process_message", json=test_data)
        end_time = time.time()
        
        if response3.status_code == 200:
            result3 = response3.json()
            print(f"✅ Third response: {result3.get('question', 'No question')[:50]}...")
            print(f"⏱️  Time taken: {(end_time - start_time):.2f}s")
        else:
            print(f"❌ Third request failed: {response3.status_code}")
        
    except Exception as e:
        print(f"❌ Error testing server throttle: {str(e)}")
        print("💡 Make sure the Flask server is running on port 8000")

def demonstrate_throttle_benefits():
    """Demonstrate the benefits of throttling"""
    print(f"\n📊 Throttle Benefits Demonstration")
    print("=" * 50)
    
    print("🎯 Benefits of Email Throttling:")
    print("1. ⏰ Prevents rapid-fire email sending")
    print("2. 🚫 Reduces duplicate email issues")
    print("3. 📧 Better user experience")
    print("4. 🔄 Alternating timing (1s/3s) prevents patterns")
    print("5. 💰 Reduces API costs and email delivery issues")
    
    print(f"\n⚙️  Throttle Configuration:")
    print("- Minimum interval: 3 seconds")
    print("- Even seconds: 1 second wait")
    print("- Odd seconds: 3 seconds wait")
    print("- Per-user tracking")
    
    print(f"\n📈 Expected Results:")
    print("- No more duplicate emails within 3 seconds")
    print("- Better email delivery success rates")
    print("- Reduced server load")
    print("- More predictable email timing")

if __name__ == "__main__":
    # Test the throttle logic
    test_throttle_logic()
    
    # Demonstrate benefits
    demonstrate_throttle_benefits()
    
    # Test with actual server (if available)
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            test_server_throttle()
        else:
            print("\n💡 Flask server not available - skipping server integration test")
    except:
        print("\n💡 Flask server not available - skipping server integration test")
        print("💡 To test with server, run: source venv/bin/activate && python langgraph_server.py") 