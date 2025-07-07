#!/usr/bin/env python3
"""
Test task processing with actual data
"""

import os
import json
import requests

def test_task_creation():
    # Your actual task data
    task_data = {
        "custemail": "richard.genet@gmail.com",
        "phone": "@PoorRichard808",
        "Posted": "",
        "DueDate": "7/8/2025, 12:00:00 AM",
        "Task": "t449",
        "description": "d",
        "Category": "Bathrooms/Showers",
        "FullAddress": "",
        "Task Budget": 11,
        "State": "GA",
        "vendors": ""
    }
    
    print("📋 Task Data:")
    print(json.dumps(task_data, indent=2))
    
    # Test the unified task processor
    url = "https://unified-task-processor-cs64iuly6q-uc.a.run.app/process_task"
    
    try:
        print(f"\n🚀 Sending to: {url}")
        response = requests.post(url, json=task_data, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Error Response: {response.text}")
            try:
                error_data = response.json()
                print(f"❌ Error Details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"❌ Raw Error: {response.text}")
                
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def test_direct_telegram_send():
    """Test sending message directly to the known chat_id"""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return
    
    base_url = f"https://api.telegram.org/bot{bot_token}"
    url = f"{base_url}/sendMessage"
    
    # Use the known working chat_id
    payload = {
        'chat_id': '7321828510',
        'text': 'Hello Richard! This is a test message from the debug tool.'
    }
    
    print(f"\n🔍 Testing direct Telegram send to chat_id: 7321828510")
    print(f"📤 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "direct":
        test_direct_telegram_send()
    else:
        test_task_creation() 