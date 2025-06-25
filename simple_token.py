#!/usr/bin/env python3
"""
Simple Firebase token generator - alternative approach
"""

import firebase_admin
from firebase_admin import credentials, auth
import requests
import json
import os

def generate_simple_token():
    """Generate a Firebase ID token using a simpler approach"""
    
    try:
        # Initialize Firebase Admin SDK
        service_account_path = os.path.expanduser("~/fbserviceAccountKey-admin.json")
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {'projectId': 'prizmpoc'})
        
        print("✅ Firebase Admin SDK initialized")
        
        # Create a custom token with a simple UID
        test_uid = "test-user-123"
        custom_token = auth.create_custom_token(test_uid)
        custom_token_str = custom_token.decode()
        
        print(f"✅ Custom token created")
        
        # Exchange using a simpler approach
        api_key = "AIzaSyCyO4TZBIILJeJcVXBaB1rEWPWBbhb2WA8"
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
        
        payload = {
            "token": custom_token_str,
            "returnSecureToken": True
        }
        
        print("🔄 Exchanging token...")
        
        # Use a shorter timeout
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            id_token = result.get("idToken")
            
            if id_token:
                print("✅ ID token generated!")
                print(f"🔑 Token: {id_token[:50]}...")
                
                # Test the cloud function
                test_url = "https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email"
                test_headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {id_token}"
                }
                test_data = {
                    "userEmail": "test@prizmpoc.com",
                    "userResponse": "I need a 3-bedroom house in downtown area",
                    "taskTitle": "Find a house"
                }
                
                print("\n🧪 Testing cloud function...")
                test_response = requests.post(test_url, json=test_data, headers=test_headers, timeout=30)
                
                print(f"📊 Status: {test_response.status_code}")
                print(f"📄 Response: {test_response.text}")
                
                return id_token
            else:
                print("❌ No ID token in response")
                return None
        else:
            print(f"❌ Exchange failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Simple Firebase Token Generator")
    print("=" * 40)
    generate_simple_token() 