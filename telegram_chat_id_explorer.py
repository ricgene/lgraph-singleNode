#!/usr/bin/env python3
"""
Telegram Chat ID Explorer
Utility to understand and explore chat_id behavior in Telegram

This helps you understand:
- What chat_id looks like for different types of chats
- How to store and retrieve chat_ids
- Best practices for chat_id management
"""

import os
import requests
import json
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatIDExplorer:
    """Explore and understand Telegram chat_id behavior"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
    def get_me(self) -> Dict:
        """Get bot information"""
        url = f"{self.base_url}/getMe"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get bot info: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_updates(self, limit: int = 10) -> Dict:
        """Get recent updates to see chat_id examples"""
        url = f"{self.base_url}/getUpdates"
        params = {"limit": limit}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get updates: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def send_message(self, chat_id: str, text: str) -> Dict:
        """Send a message to test chat_id"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_chat(self, chat_id: str) -> Dict:
        """Get information about a specific chat"""
        url = f"{self.base_url}/getChat"
        params = {"chat_id": chat_id}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get chat info: {str(e)}")
            return {"ok": False, "error": str(e)}

def analyze_chat_id(chat_id: int) -> Dict:
    """Analyze a chat_id to determine its type and characteristics"""
    
    chat_id_str = str(chat_id)
    
    if chat_id > 0:
        return {
            "type": "private_chat",
            "description": "One-on-one conversation with a user",
            "characteristics": [
                "Fixed for life (never changes)",
                "Unique per user-bot combination",
                "Can be used to send messages to that specific user",
                "Stays the same even if user changes username"
            ],
            "storage_recommendation": "Store permanently - never expires"
        }
    
    elif chat_id_str.startswith("-100"):
        return {
            "type": "channel",
            "description": "Broadcast channel",
            "characteristics": [
                "Fixed as long as channel exists",
                "All subscribers see messages sent here",
                "Bot must be admin to send messages",
                "High negative number (starts with -100)"
            ],
            "storage_recommendation": "Store permanently - channel ID is stable"
        }
    
    else:
        return {
            "type": "group_chat",
            "description": "Group conversation",
            "characteristics": [
                "Fixed as long as group exists",
                "All group members see messages",
                "Bot must be member to send messages",
                "Negative number (but not starting with -100)"
            ],
            "storage_recommendation": "Store permanently - group ID is stable"
        }

def explore_recent_chats():
    """Explore recent chat interactions to understand chat_id patterns"""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    explorer = ChatIDExplorer(bot_token)
    
    # Get bot info
    bot_info = explorer.get_me()
    if not bot_info.get('ok'):
        logger.error(f"❌ Failed to get bot info: {bot_info}")
        return
    
    bot_name = bot_info['result']['first_name']
    bot_username = bot_info['result']['username']
    logger.info(f"🤖 Bot: {bot_name} (@{bot_username})")
    
    # Get recent updates
    updates = explorer.get_updates(limit=20)
    if not updates.get('ok'):
        logger.error(f"❌ Failed to get updates: {updates}")
        return
    
    chat_examples = {}
    
    for update in updates.get('result', []):
        message = update.get('message', {})
        if not message:
            continue
        
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        chat_type = chat.get('type')
        title = chat.get('title', '')
        username = chat.get('username', '')
        first_name = chat.get('first_name', '')
        last_name = chat.get('last_name', '')
        
        if chat_id not in chat_examples:
            chat_examples[chat_id] = {
                'chat_id': chat_id,
                'type': chat_type,
                'title': title,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'analysis': analyze_chat_id(chat_id)
            }
    
    if not chat_examples:
        logger.info("📭 No recent chat interactions found")
        logger.info("💡 Send a message to your bot to see chat_id examples")
        return
    
    logger.info(f"📊 Found {len(chat_examples)} unique chat examples:")
    logger.info("=" * 60)
    
    for chat_id, info in chat_examples.items():
        logger.info(f"🆔 Chat ID: {chat_id}")
        logger.info(f"📝 Type: {info['analysis']['type']}")
        logger.info(f"📋 Description: {info['analysis']['description']}")
        
        if info['type'] == 'private':
            display_name = f"{info['first_name']} {info['last_name']}".strip()
            if info['username']:
                display_name += f" (@{info['username']})"
            logger.info(f"👤 User: {display_name}")
        elif info['type'] == 'group':
            logger.info(f"👥 Group: {info['title']}")
            if info['username']:
                logger.info(f"🔗 Username: @{info['username']}")
        elif info['type'] == 'channel':
            logger.info(f"📢 Channel: {info['title']}")
            if info['username']:
                logger.info(f"🔗 Username: @{info['username']}")
        
        logger.info(f"💾 Storage: {info['analysis']['storage_recommendation']}")
        logger.info("=" * 60)

def demonstrate_chat_id_persistence():
    """Demonstrate that chat_id remains the same"""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    explorer = ChatIDExplorer(bot_token)
    
    logger.info("🔍 Chat ID Persistence Demonstration")
    logger.info("=" * 50)
    logger.info("1. Chat ID is FIXED for a user-bot combination")
    logger.info("2. It never changes, even if user changes username")
    logger.info("3. You can store it permanently in your database")
    logger.info("4. It's the most reliable way to reach a specific user")
    logger.info("")
    logger.info("📊 Chat ID Examples by Type:")
    logger.info("")
    
    examples = [
        {"chat_id": 123456789, "description": "Private chat with user"},
        {"chat_id": -987654321, "description": "Group chat"},
        {"chat_id": -1001234567890, "description": "Channel"}
    ]
    
    for example in examples:
        analysis = analyze_chat_id(example['chat_id'])
        logger.info(f"🆔 {example['chat_id']} - {analysis['type']}")
        logger.info(f"   📝 {example['description']}")
        logger.info(f"   💾 {analysis['storage_recommendation']}")
        logger.info("")

def show_best_practices():
    """Show best practices for chat_id management"""
    
    logger.info("🏆 Best Practices for Chat ID Management")
    logger.info("=" * 50)
    logger.info("")
    logger.info("✅ DO:")
    logger.info("   • Store chat_id permanently in your database")
    logger.info("   • Use chat_id as the primary key for user identification")
    logger.info("   • Cache chat_id for fast message sending")
    logger.info("   • Handle different chat types appropriately")
    logger.info("")
    logger.info("❌ DON'T:")
    logger.info("   • Rely on username (users can change it)")
    logger.info("   • Assume chat_id will change")
    logger.info("   • Store only username without chat_id")
    logger.info("   • Use display names for identification")
    logger.info("")
    logger.info("🔧 Implementation Tips:")
    logger.info("   • Create a users table with chat_id as primary key")
    logger.info("   • Store username as secondary reference")
    logger.info("   • Implement chat_id lookup for fast message sending")
    logger.info("   • Handle group/channel permissions appropriately")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "explore":
            explore_recent_chats()
        elif command == "persistence":
            demonstrate_chat_id_persistence()
        elif command == "best-practices":
            show_best_practices()
        else:
            print("Usage: python telegram_chat_id_explorer.py [explore|persistence|best-practices]")
    else:
        # Run all demonstrations
        demonstrate_chat_id_persistence()
        show_best_practices()
        print("\n" + "="*60)
        print("💡 Run 'python telegram_chat_id_explorer.py explore' to see your actual chat examples") 