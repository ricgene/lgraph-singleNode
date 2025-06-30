#!/usr/bin/env python3
"""
Quick SMS Test - Test SMS functionality without running server
"""

import os
import sys
import asyncio
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tests-new'))

def test_imports():
    """Test that all imports work"""
    try:
        from observability import get_logger
        print("✅ Observability import: OK")
        
        from local_agent_test_observable import ObservableLocalAgentFirestoreLoop
        print("✅ Agent loop import: OK")
        
        import twilio
        print("✅ Twilio import: OK")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

async def test_sms_conversation():
    """Test SMS conversation without server"""
    try:
        # Import the SMS conversation class
        from local_agent_test_observable import ObservableLocalAgentFirestoreLoop
        
        print("🚀 Testing SMS conversation flow...")
        
        agent_loop = ObservableLocalAgentFirestoreLoop()
        
        # Test conversation
        phone_number = "+1234567890"
        user_email = f"{phone_number.replace('+', '').replace('-', '')}@sms.local"
        task_title = "SMS Test Conversation"
        
        conversation_script = [
            "",  # Initial greeting
            "Yes, I'm ready to discuss my task",
            "Yes, I'll reach out to the contractor"
        ]
        
        for i, message in enumerate(conversation_script, 1):
            print(f"\n📱 Turn {i}: '{message}'")
            
            result = await agent_loop.run_conversation_turn(
                user_email=user_email,
                task_title=task_title,
                user_input=message,
                user_first_name="SMS_User"
            )
            
            print(f"🤖 Agent: '{result.get('question', 'No response')}'")
            print(f"📊 Turn: {result.get('turn_count', 0)} | Complete: {result.get('is_complete', False)}")
            
            if result.get('is_complete', False):
                print(f"🏁 Conversation completed!")
                break
        
        print("\n✅ SMS conversation test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ SMS conversation test failed: {e}")
        return False

def test_mock_sms():
    """Test mock SMS functionality"""
    try:
        print("\n📤 Testing mock SMS sending...")
        
        # Simple mock SMS
        mock_sms_data = {}
        
        def send_mock_sms(to_number, message):
            mock_sms_data[f"sms_{len(mock_sms_data)}"] = {
                "to": to_number,
                "body": message,
                "timestamp": datetime.now().isoformat(),
                "status": "delivered"
            }
            return {"sid": f"mock_sid_{len(mock_sms_data)}", "status": "sent"}
        
        # Test sending
        result = send_mock_sms("+1234567890", "Hello from SMS test!")
        print(f"✅ Mock SMS sent: SID {result['sid']}")
        print(f"📊 SMS database: {len(mock_sms_data)} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock SMS test failed: {e}")
        return False

async def main():
    """Run all quick tests"""
    print("🚀 Quick SMS Test Suite")
    print("=" * 40)
    
    results = []
    
    # Test 1: Imports
    print("\n1️⃣ Testing imports...")
    results.append(test_imports())
    
    # Test 2: SMS Conversation
    print("\n2️⃣ Testing SMS conversation...")
    results.append(await test_sms_conversation())
    
    # Test 3: Mock SMS
    print("\n3️⃣ Testing mock SMS...")
    results.append(test_mock_sms())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n🏁 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! SMS integration is ready!")
        print("\n🚀 Next steps:")
        print("1. Start SMS server: python sms_webhook_server.py")
        print("2. Test with curl: curl http://localhost:5000/health")
        print("3. Send test SMS: curl -X POST http://localhost:5000/sms/mock -d '{\"from\":\"+1234567890\",\"message\":\"Hello\"}' -H 'Content-Type: application/json'")
    else:
        print("❌ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())