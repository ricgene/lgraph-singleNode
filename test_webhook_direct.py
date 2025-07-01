#!/usr/bin/env python3
"""
Direct webhook testing without ngrok
Test the SMS webhook endpoints directly
"""

import requests
import json
import time

def test_webhook_status():
    """Test the webhook server status"""
    try:
        response = requests.get("http://localhost:5000/sms/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Webhook server is running!")
            print(f"📱 SMS Provider: {data.get('sms_provider', 'unknown')}")
            print(f"📱 MessageCentral: {data.get('messagecentral_enabled', False)}")
            print(f"📱 Twilio configured: {data.get('twilio_configured', False)}")
            return True
        else:
            print(f"❌ Webhook server error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Webhook server not accessible: {str(e)}")
        return False

def test_sms_send():
    """Test SMS sending endpoint"""
    try:
        payload = {
            "to": "+18777804236",
            "message": "🧪 Direct webhook SMS test - production ready!"
        }
        
        response = requests.post(
            "http://localhost:5000/sms/send", 
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SMS send endpoint working!")
            print(f"📧 Message ID: {data.get('sid', 'N/A')}")
            print(f"📊 Status: {data.get('status', 'N/A')}")
            return True
        else:
            print(f"❌ SMS send failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ SMS send error: {str(e)}")
        return False

def test_mock_conversation():
    """Test mock SMS conversation"""
    try:
        payload = {
            "from": "+18777804236",
            "message": "Hello! I need help with my home task."
        }
        
        response = requests.post(
            "http://localhost:5000/sms/mock",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Mock conversation working!")
            print(f"👤 User: {data['conversation']['user_input']}")
            print(f"🤖 Agent: {data['conversation']['agent_response']}")
            print(f"🔄 Turn: {data['conversation']['turn_count']}")
            return True
        else:
            print(f"❌ Mock conversation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Mock conversation error: {str(e)}")
        return False

def main():
    print("🧪 Direct Webhook Testing (Without ngrok)")
    print("=" * 50)
    
    tests = [
        ("Webhook Server Status", test_webhook_status),
        ("SMS Send Endpoint", test_sms_send),
        ("Mock Conversation", test_mock_conversation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🚀 Testing: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: ERROR - {str(e)}")
        
        time.sleep(1)  # Brief pause between tests
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All webhook tests passed!")
        print("📱 SMS system is production-ready for MessageCentral")
        print("\nFor real SMS webhook testing:")
        print("1. Get ngrok account: https://dashboard.ngrok.com/signup")
        print("2. Set authtoken: ./ngrok config add-authtoken YOUR_TOKEN")
        print("3. Start tunnel: ./ngrok http 5000")
        print("4. Configure MessageCentral webhook URL")
    else:
        print("⚠️ Some tests failed. Check the webhook server logs.")

if __name__ == "__main__":
    main()