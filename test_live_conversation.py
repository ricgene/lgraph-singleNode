#!/usr/bin/env python3
"""
Test live SMS conversation via ngrok tunnel
"""

import requests
import json
import time

def test_conversation_flow():
    """Test a complete SMS conversation flow"""
    
    # Use the ngrok URL
    base_url = "https://a109-99-1-34-236.ngrok-free.app"
    
    print("🧪 Testing Live SMS Conversation Flow")
    print("=" * 50)
    print(f"🌐 Using ngrok tunnel: {base_url}")
    
    # Test 1: Mock incoming SMS
    print("\n📲 Step 1: Simulating incoming SMS...")
    
    payload = {
        "from": "+18777804236",
        "message": "Hi Helen! I need help with my kitchen repair task."
    }
    
    try:
        response = requests.post(
            f"{base_url}/sms/mock",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Mock SMS conversation successful!")
            print(f"👤 User: {data['conversation']['user_input']}")
            print(f"🤖 Agent: {data['conversation']['agent_response']}")
            print(f"🔄 Turn: {data['conversation']['turn_count']}")
            
            # Test 2: Send real SMS response
            print("\n📤 Step 2: Sending real SMS response...")
            
            sms_payload = {
                "to": "+18777804236",
                "message": data['conversation']['agent_response']
            }
            
            sms_response = requests.post(
                f"{base_url}/sms/send",
                json=sms_payload,
                timeout=30
            )
            
            if sms_response.status_code == 200:
                sms_data = sms_response.json()
                print("✅ Real SMS sent successfully!")
                print(f"📧 Message ID: {sms_data.get('sid', 'N/A')}")
                print(f"📊 Status: {sms_data.get('status', 'N/A')}")
                
                print("\n🎉 Complete conversation flow working!")
                print("📱 The system can:")
                print("  1. Receive incoming SMS (mock tested)")
                print("  2. Process with AI agent")
                print("  3. Send real SMS responses")
                
                return True
            else:
                print(f"❌ SMS send failed: {sms_response.status_code}")
                return False
                
        else:
            print(f"❌ Mock conversation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def test_webhook_ready():
    """Test if webhook is ready for MessageCentral"""
    
    base_url = "https://a109-99-1-34-236.ngrok-free.app"
    
    print("\n🔗 Testing Webhook Readiness for MessageCentral")
    print("-" * 40)
    
    try:
        # Test webhook endpoint accessibility
        response = requests.get(f"{base_url}/sms/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Webhook endpoint accessible!")
            print(f"📱 SMS Provider: {data.get('sms_provider', 'unknown')}")
            print(f"📡 Status: {data.get('status', 'unknown')}")
            
            print(f"\n📋 MessageCentral Webhook Configuration:")
            print(f"   URL: {base_url}/sms/webhook")
            print(f"   Method: POST")
            print(f"   Content-Type: application/x-www-form-urlencoded")
            
            return True
        else:
            print(f"❌ Webhook not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Webhook test failed: {str(e)}")
        return False

def main():
    """Run live conversation tests"""
    
    # Test conversation flow
    conversation_success = test_conversation_flow()
    
    # Test webhook readiness
    webhook_success = test_webhook_ready()
    
    print("\n" + "=" * 50)
    print("📊 Live Testing Results:")
    print(f"  Conversation Flow: {'✅ PASSED' if conversation_success else '❌ FAILED'}")
    print(f"  Webhook Ready: {'✅ READY' if webhook_success else '❌ NOT READY'}")
    
    if conversation_success and webhook_success:
        print("\n🎉 SYSTEM IS LIVE AND READY!")
        print("📱 Next step: Configure MessageCentral webhook")
        print("   Or send a real SMS to test the system!")
    else:
        print("\n⚠️ Some tests failed - check the logs")

if __name__ == "__main__":
    main()