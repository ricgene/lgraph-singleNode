#!/usr/bin/env python3
"""
Send SMS to your actual phone number
"""

import sys
sys.path.append('.')

from messagecentral_sms import MessageCentralSMS

def send_test_sms():
    """Send test SMS to your phone"""
    
    print("📱 Sending SMS to your phone: +1 404 376 0553")
    print("=" * 40)
    
    # Initialize MessageCentral client
    mc_client = MessageCentralSMS()
    
    # Your actual phone number
    your_phone = "+14043760553"
    
    # Test message
    message = "🤖 Hello! This is Helen, your AI assistant. Your SMS conversation system is now LIVE and ready to help with home tasks!"
    
    # Send SMS
    result = mc_client.send_sms(your_phone, message)
    
    if result["status"] == "sent":
        print("✅ SMS sent successfully to your phone!")
        print(f"📧 Message ID: {result['sid']}")
        print(f"📧 Transaction ID: {result.get('transaction_id', 'N/A')}")
        print("\n📱 Check your phone for the message!")
        return True
    else:
        print(f"❌ SMS failed: {result.get('error', 'Unknown error')}")
        return False

if __name__ == "__main__":
    send_test_sms()