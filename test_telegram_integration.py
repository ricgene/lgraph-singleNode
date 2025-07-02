#!/usr/bin/env python3
"""
Test script for Telegram Bot integration
Tests webhook handling, message processing, and LangGraph integration
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', 'http://localhost:5000/telegram/webhook')
LOCAL_SERVER_URL = os.getenv('LOCAL_SERVER_URL', 'http://localhost:5000')

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/telegram/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False

def test_webhook_info():
    """Test getting webhook information"""
    print("ℹ️ Testing webhook info...")
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/telegram/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Webhook info: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Webhook info failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Webhook info error: {str(e)}")
        return False

def test_mock_webhook():
    """Test webhook with mock Telegram message"""
    print("📨 Testing mock webhook message...")
    
    # Create a mock Telegram update
    mock_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 987654321,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "Hello, this is a test message!"
        }
    }
    
    try:
        response = requests.post(
            f"{LOCAL_SERVER_URL}/telegram/webhook",
            json=mock_update,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Webhook test passed: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Webhook test failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Webhook test error: {str(e)}")
        return False

def test_start_command():
    """Test /start command"""
    print("🚀 Testing /start command...")
    
    mock_update = {
        "update_id": 123456790,
        "message": {
            "message_id": 2,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 987654321,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "/start"
        }
    }
    
    try:
        response = requests.post(
            f"{LOCAL_SERVER_URL}/telegram/webhook",
            json=mock_update,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ /start command test passed: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ /start command test failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ /start command test error: {str(e)}")
        return False

def test_help_command():
    """Test /help command"""
    print("❓ Testing /help command...")
    
    mock_update = {
        "update_id": 123456791,
        "message": {
            "message_id": 3,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 987654321,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "/help"
        }
    }
    
    try:
        response = requests.post(
            f"{LOCAL_SERVER_URL}/telegram/webhook",
            json=mock_update,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ /help command test passed: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ /help command test failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ /help command test error: {str(e)}")
        return False

def setup_webhook():
    """Setup the Telegram webhook (requires bot token)"""
    print("🔧 Setting up Telegram webhook...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set, skipping webhook setup")
        return False
    
    try:
        payload = {
            "webhook_url": TELEGRAM_WEBHOOK_URL
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/telegram/setup",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Webhook setup successful: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Webhook setup failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Webhook setup error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🤖 Starting Telegram Bot Integration Tests")
    print("=" * 50)
    
    # Configuration check
    print(f"🔧 Configuration:")
    print(f"   Bot Token: {'✅ Set' if TELEGRAM_BOT_TOKEN else '❌ Missing'}")
    print(f"   Webhook URL: {TELEGRAM_WEBHOOK_URL}")
    print(f"   Local Server: {LOCAL_SERVER_URL}")
    print()
    
    tests = [
        ("Health Check", test_health_check),
        ("Webhook Info", test_webhook_info),
        ("Mock Message", test_mock_webhook),
        ("/start Command", test_start_command),
        ("/help Command", test_help_command),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            results[test_name] = False
        print()
    
    # Optional webhook setup (only if token is available)
    if TELEGRAM_BOT_TOKEN:
        print("Running Webhook Setup...")
        try:
            results["Webhook Setup"] = setup_webhook()
        except Exception as e:
            print(f"❌ Webhook Setup crashed: {str(e)}")
            results["Webhook Setup"] = False
        print()
    
    # Summary
    print("📊 Test Results Summary")
    print("=" * 30)
    passed = 0
    total = 0
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        total += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the logs above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())