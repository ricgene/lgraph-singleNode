#!/usr/bin/env python3
"""
Check Firestore mapping for Telegram username
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore

def check_telegram_mapping():
    # Initialize Firebase
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    # Check for @PoorRichard808 mapping
    username = "poorrichard808"  # lowercase, no @
    doc_ref = db.collection('telegram_users').document(username)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        print(f"✅ Found mapping for @{username}:")
        print(f"   Chat ID: {data.get('chat_id')}")
        print(f"   Last seen: {data.get('last_seen')}")
        print(f"   User data: {data.get('user_data', {})}")
        
        # Test if this chat_id is valid
        chat_id = data.get('chat_id')
        if chat_id:
            print(f"\n🔍 Testing chat_id: {chat_id}")
            test_chat_id(chat_id)
    else:
        print(f"❌ No mapping found for @{username}")
        print("💡 User needs to message @Aloha116bot first")

def test_chat_id(chat_id):
    """Test if a chat_id is valid"""
    import requests
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return
    
    base_url = f"https://api.telegram.org/bot{bot_token}"
    url = f"{base_url}/getChat"
    params = {"chat_id": chat_id}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Chat ID {chat_id} is valid")
                chat_data = result['result']
                print(f"   Type: {chat_data.get('type')}")
                print(f"   Title: {chat_data.get('title', 'N/A')}")
                print(f"   Username: @{chat_data.get('username', 'N/A')}")
            else:
                print(f"❌ Chat ID {chat_id} is invalid: {result.get('description')}")
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error testing chat_id: {str(e)}")

if __name__ == "__main__":
    check_telegram_mapping() 