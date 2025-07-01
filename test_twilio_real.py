#!/usr/bin/env python3
"""
Test Real Twilio SMS Integration
"""

import os
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

def test_twilio_credentials():
    """Test Twilio credentials and send a test SMS"""
    
    # Get credentials from environment
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    print("🔧 Testing Twilio Credentials...")
    print(f"Account SID: {account_sid}")
    print(f"From Number: {from_number}")
    print(f"Auth Token: {auth_token[:8]}...")
    
    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Test connection by getting account info
        account = client.api.accounts(account_sid).fetch()
        print(f"✅ Twilio connection successful!")
        print(f"📱 Account Status: {account.status}")
        print(f"📱 Account Name: {account.friendly_name}")
        
        return client
        
    except Exception as e:
        print(f"❌ Twilio connection failed: {e}")
        return None

def send_test_sms(client, to_number):
    """Send a test SMS"""
    
    from_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    try:
        print(f"\n📤 Sending test SMS to {to_number}...")
        
        message = client.messages.create(
            from_=from_number,
            body='🤖 Hello from your SMS Agent! This is a test message from your local development server.',
            to=to_number
        )
        
        print(f"✅ SMS sent successfully!")
        print(f"📧 Message SID: {message.sid}")
        print(f"📊 Status: {message.status}")
        
        return message
        
    except Exception as e:
        print(f"❌ SMS send failed: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Real Twilio SMS Test")
    print("=" * 40)
    
    # Test credentials
    client = test_twilio_credentials()
    
    if not client:
        print("❌ Cannot proceed without valid Twilio connection")
        return
    
    # Get test phone number
    test_number = input("\n📱 Enter phone number to test (e.g., +18777804236): ").strip()
    
    if not test_number:
        print("❌ No phone number provided")
        return
    
    if not test_number.startswith('+'):
        print("⚠️ Adding + prefix to phone number")
        test_number = '+' + test_number
    
    # Send test SMS
    message = send_test_sms(client, test_number)
    
    if message:
        print(f"\n🎉 Test completed successfully!")
        print(f"💡 Next steps:")
        print(f"1. Check your phone for the test message")
        print(f"2. Start SMS webhook server: python sms_webhook_server.py")
        print(f"3. Set up ngrok tunnel for webhook testing")
    else:
        print(f"\n❌ Test failed - check your credentials and phone number")

if __name__ == "__main__":
    main()