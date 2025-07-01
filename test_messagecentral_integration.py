#!/usr/bin/env python3
"""
Test MessageCentral Integration with SMS Webhook Server
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_messagecentral_direct():
    """Test MessageCentral SMS directly"""
    print("🚀 Testing MessageCentral Direct SMS")
    print("=" * 40)
    
    from messagecentral_sms import MessageCentralSMS
    
    mc_client = MessageCentralSMS()
    
    # Test SMS send
    test_number = "+18777804236"
    test_message = "🔄 SMS integration test: MessageCentral + Webhook Server ready!"
    
    result = mc_client.send_sms(test_number, test_message)
    
    if result["status"] == "sent":
        print(f"✅ Direct MessageCentral SMS successful!")
        print(f"📧 Message ID: {result['sid']}")
        print(f"📧 Transaction ID: {result.get('transaction_id', 'N/A')}")
        return True
    else:
        print(f"❌ Direct MessageCentral SMS failed: {result.get('error', 'Unknown error')}")
        return False

def test_webhook_server_integration():
    """Test the webhook server SMS sending"""
    print("\n🔧 Testing Webhook Server Integration")
    print("=" * 40)
    
    try:
        # Import webhook server components
        from sms_webhook_server import send_sms_response, USE_MESSAGECENTRAL
        
        print(f"📱 MessageCentral enabled: {USE_MESSAGECENTRAL}")
        
        # Test SMS send through webhook server
        test_number = "+18777804236"
        test_message = "🔗 Webhook server SMS test via MessageCentral!"
        
        result = send_sms_response(test_number, test_message)
        
        if result and result.get("status") in ["sent", "delivered"]:
            print(f"✅ Webhook server SMS successful!")
            print(f"📧 Message ID: {result.get('sid', 'N/A')}")
            return True
        else:
            print(f"❌ Webhook server SMS failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Webhook server test error: {str(e)}")
        return False

def test_mock_conversation_flow():
    """Test a mock SMS conversation flow"""
    print("\n🤖 Testing Mock SMS Conversation Flow")
    print("=" * 40)
    
    try:
        # Import conversation components
        from sms_webhook_server import SMSConversationLoop, MockTwilioSMS
        
        # Initialize conversation loop
        sms_loop = SMSConversationLoop()
        
        # Test conversation
        test_phone = "+18777804236"
        test_message = "Hi there! Can you help me with a test question?"
        
        # Run conversation turn
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            sms_loop.process_sms_message(test_phone, test_message)
        )
        
        agent_response = result.get('question', 'No response')
        
        print(f"📲 User message: {test_message}")
        print(f"🤖 Agent response: {agent_response}")
        print(f"🔄 Turn count: {result.get('turn_count', 0)}")
        print(f"✅ Conversation complete: {result.get('is_complete', False)}")
        
        # Mock sending the response
        mock_result = MockTwilioSMS.send_sms(test_phone, agent_response)
        print(f"📤 Mock SMS sent: {mock_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversation flow test error: {str(e)}")
        return False

def main():
    """Run all integration tests"""
    print("🧪 MessageCentral + Webhook Server Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Direct MessageCentral SMS", test_messagecentral_direct),
        ("Webhook Server Integration", test_webhook_server_integration),
        ("Mock Conversation Flow", test_mock_conversation_flow)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
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
        
        print("-" * 40)
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! MessageCentral integration is ready.")
        print("\nNext steps:")
        print("1. Start webhook server: python sms_webhook_server.py")
        print("2. Set up ngrok tunnel: ngrok http 5000")
        print("3. Configure MessageCentral webhook URL")
        print("4. Test real SMS conversations!")
    else:
        print("⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()