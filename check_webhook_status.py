#!/usr/bin/env python3
"""
Quick webhook status checker
"""

import os
import requests
import json

def check_webhook_status():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return
    
    base_url = f"https://api.telegram.org/bot{bot_token}"
    
    # Get webhook info
    url = f"{base_url}/getWebhookInfo"
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        print("🔍 Webhook Status:")
        print(json.dumps(result, indent=2))
        
        if result.get('ok') and result.get('result', {}).get('url'):
            print(f"\n✅ Webhook is set to: {result['result']['url']}")
            
            # Ask if user wants to delete webhook
            choice = input("\n❓ Do you want to delete the webhook to use polling? (y/n): ")
            if choice.lower() == 'y':
                delete_url = f"{base_url}/deleteWebhook"
                delete_response = requests.post(delete_url, timeout=10)
                delete_result = delete_response.json()
                print(f"🗑️ Delete result: {json.dumps(delete_result, indent=2)}")
                
                if delete_result.get('ok'):
                    print("✅ Webhook deleted successfully!")
                    print("🔄 Now you can use polling mode")
        else:
            print("ℹ️ No webhook is set")
            
    except Exception as e:
        print(f"❌ Error checking webhook: {str(e)}")

if __name__ == "__main__":
    check_webhook_status() 