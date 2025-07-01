#!/usr/bin/env python3
"""
Simple Twilio SMS Test - Non-interactive
"""

import os
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

def test_and_send():
    """Test Twilio and send SMS to your number"""
    
    # Get credentials
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')
    to_number = "+18777804236"  # Your number from the example
    
    print("🚀 Testing Real Twilio SMS")
    print("=" * 30)
    print(f"From: {from_number}")
    print(f"To: {to_number}")
    
    try:
        # Initialize client
        client = Client(account_sid, auth_token)
        
        # Send test message
        message = client.messages.create(
            from_=from_number,
            body='🤖 SMS Agent Test: Your conversation system is ready! Reply to start a conversation.',
            to=to_number
        )
        
        print(f"✅ SMS sent successfully!")
        print(f"📧 Message SID: {message.sid}")
        print(f"📊 Status: {message.status}")
        
        print(f"\n🎉 Success! Next steps:")
        print(f"1. Check your phone for the message")
        print(f"2. Start webhook server: python sms_webhook_server.py")
        print(f"3. Install ngrok: brew install ngrok (or download)")
        print(f"4. Run ngrok: ngrok http 5000")
        print(f"5. Configure Twilio webhook with ngrok URL")
        
        return True
        
    except Exception as e:
        print(f"❌ SMS failed: {e}")
        return False

if __name__ == "__main__":
    test_and_send()