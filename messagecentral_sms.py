#!/usr/bin/env python3
"""
MessageCentral SMS Integration
Based on official MessageCentral API documentation
"""

import os
import json
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MessageCentralSMS:
    """MessageCentral SMS API client"""
    
    def __init__(self):
        self.base_url = "https://cpaas.messagecentral.com"
        self.customer_id = os.getenv('MC_CUSTOMER_ID')
        self.password = os.getenv('MC_PASSWORD')
        self.password_base64 = os.getenv('MC_PASSWORD_BASE64')
        self.token = None  # Will be generated
        
    def generate_token(self):
        """Generate authentication token using MessageCentral API"""
        url = f"{self.base_url}/auth/v1/authentication/token"
        
        params = {
            'customerId': self.customer_id,
            'key': self.password_base64,
            'scope': 'NEW',
            'country': '91'  # Default to India, adjust as needed
        }
        
        headers = {
            'accept': '*/*'
        }
        
        try:
            print(f"🔐 Generating MessageCentral token...")
            print(f"Customer ID: {self.customer_id}")
            print(f"Base64 Key: {self.password_base64}")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 200:
                    self.token = result.get('token')
                    print(f"✅ Token generated successfully!")
                    print(f"🔑 Token: {self.token[:20]}...")
                    return True
                else:
                    print(f"❌ Token generation failed: {result}")
                    return False
            else:
                print(f"❌ Token request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Token generation error: {str(e)}")
            return False
    
    def send_sms(self, to_number: str, message: str, sender_id: str = "UTOMOB"):
        """Send SMS via MessageCentral API"""
        
        # Generate token if not available
        if not self.token:
            if not self.generate_token():
                return {"sid": None, "status": "error", "error": "Token generation failed"}
        
        # MessageCentral SMS API endpoint
        url = f"{self.base_url}/verification/v3/send"
        
        # Clean phone number (remove + and other characters)
        clean_number = to_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # Extract country code and mobile number
        if clean_number.startswith('91'):
            country_code = "91"
            mobile_number = clean_number[2:]
        elif clean_number.startswith('1'):
            country_code = "1"
            mobile_number = clean_number[1:]
        else:
            # Default to US
            country_code = "1"
            mobile_number = clean_number
        
        # Prepare parameters based on MessageCentral API docs
        params = {
            'countryCode': country_code,
            'flowType': 'SMS',
            'mobileNumber': mobile_number,
            'senderId': sender_id,
            'type': 'SMS',
            'message': message,
            'messageType': 'PROMOTIONAL'  # or TRANSACTIONAL, OTP
        }
        
        headers = {
            'authToken': self.token
        }
        
        try:
            print(f"📤 Sending SMS via MessageCentral to {to_number}")
            print(f"📝 Country: {country_code}, Mobile: {mobile_number}")
            print(f"📝 Message: {message[:50]}...")
            
            response = requests.post(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('responseCode') == 200:
                    print(f"✅ SMS sent successfully!")
                    print(f"📧 Response: {result}")
                    data = result.get('data', {})
                    return {
                        "sid": data.get("verificationId", "unknown"),
                        "status": "sent",
                        "response": result,
                        "transaction_id": data.get("transactionId", "")
                    }
                else:
                    print(f"❌ SMS send failed: {result}")
                    return {
                        "sid": None,
                        "status": "failed",
                        "error": result.get('message', 'Unknown error')
                    }
            else:
                print(f"❌ SMS send failed: {response.status_code}")
                print(f"❌ Response: {response.text}")
                return {
                    "sid": None,
                    "status": "failed",
                    "error": response.text
                }
                
        except Exception as e:
            print(f"❌ SMS send error: {str(e)}")
            return {
                "sid": None,
                "status": "error",
                "error": str(e)
            }
    
    def test_connection(self):
        """Test MessageCentral API connection"""
        try:
            # Generate token first
            if not self.token:
                self.generate_token()
            
            # Test with token generation success as connection test
            return self.token is not None
                
        except Exception as e:
            print(f"❌ MessageCentral connection error: {str(e)}")
            return False

def test_messagecentral():
    """Test MessageCentral SMS functionality"""
    print("🚀 Testing MessageCentral SMS")
    print("=" * 40)
    
    # Initialize client
    mc_client = MessageCentralSMS()
    
    print(f"Customer ID: {mc_client.customer_id}")
    print(f"Token: {mc_client.token or 'Not generated yet'}")
    
    # Test connection  
    if mc_client.test_connection():
        print("🔗 Connection test passed")
    else:
        print("⚠️ Connection test failed, but proceeding with SMS test")
    
    # Test SMS send
    test_number = "+18777804236"  # Your number
    test_message = "🤖 Hello from MessageCentral SMS! Your agent is ready for conversations."
    
    result = mc_client.send_sms(test_number, test_message)
    
    if result["status"] == "sent":
        print(f"\n🎉 SMS test successful!")
        print(f"📧 Message ID: {result['sid']}")
    else:
        print(f"\n❌ SMS test failed: {result.get('error', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    test_messagecentral()