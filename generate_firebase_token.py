#!/usr/bin/env python3
"""
Generate Firebase ID Token for testing
This script creates a custom token and exchanges it for an ID token
"""

import firebase_admin
from firebase_admin import credentials, auth
import requests
import json
import os

# Your Firebase configuration
FIREBASE_API_KEY = "AIzaSyCyO4TZBIILJeJcVXBaB1rEWPWBbhb2WA8"
PROJECT_ID = "prizmpoc"

def generate_firebase_token():
    """Generate a Firebase ID token for testing"""
    
    try:
        # Initialize Firebase Admin SDK
        # Use the existing service account key file
        service_account_path = os.path.expanduser("~/fbserviceAccountKey-admin.json")
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {'projectId': PROJECT_ID})
        
        print("✅ Firebase Admin SDK initialized")
        print(f"📁 Using service account: {service_account_path}")
        
        # Create a custom token for a test user
        # You can use any UID - this creates a test user
        test_uid = "test-service-account-user"
        custom_token = auth.create_custom_token(test_uid)
        
        print(f"✅ Custom token created for UID: {test_uid}")
        print(f"📝 Custom token: {custom_token.decode()}")
        
        # Exchange custom token for ID token
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"
        payload = {
            "token": custom_token.decode(),
            "returnSecureToken": True
        }
        
        print("🔄 Exchanging custom token for ID token...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            id_token = result.get("idToken")
            refresh_token = result.get("refreshToken")
            
            print("✅ ID token generated successfully!")
            print(f"🔑 ID Token: {id_token}")
            print(f"🔄 Refresh Token: {refresh_token}")
            
            # Create a curl command for easy testing
            curl_command = f'''curl -X POST "https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer {id_token}" \\
  -d '{{"userEmail": "test@prizmpoc.com", "userResponse": "I need a 3-bedroom house in downtown area", "taskTitle": "Find a house"}}' '''
            
            print("\n📋 Ready-to-use curl command:")
            print("=" * 50)
            print(curl_command)
            print("=" * 50)
            
            return id_token
            
        else:
            print(f"❌ Failed to exchange token: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except FileNotFoundError:
        print("❌ Error: ~/fbserviceAccountKey-admin.json not found!")
        print("📝 Please check that the file exists in your home directory")
        return None
        
    except Exception as e:
        print(f"❌ Error generating token: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Firebase ID Token Generator")
    print("=" * 40)
    
    # Check if service account key exists
    service_account_path = os.path.expanduser("~/fbserviceAccountKey-admin.json")
    if not os.path.exists(service_account_path):
        print(f"❌ {service_account_path} not found!")
        print("\n📋 Please check that your Firebase service account key file exists at:")
        print(f"   {service_account_path}")
    else:
        generate_firebase_token() 