#!/usr/bin/env python3
"""
Minimal Telegram Bot - No Firestore Required
A simple Telegram bot that works without any external database dependencies.

Requirements:
- TELEGRAM_BOT_TOKEN environment variable
- requests library (pip install requests)

Usage:
1. Set your bot token: export TELEGRAM_BOT_TOKEN="your_bot_token_here"
2. Run: python telegram_minimal_no_firestore.py
3. Send messages to your bot on Telegram
"""

import os
import requests
import json
import logging
import time
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MinimalTelegramBot:
    """Minimal Telegram bot with no external dependencies"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.user_sessions = {}  # Simple in-memory storage
        
    def send_message(self, chat_id: str, text: str) -> Dict:
        """Send a message to a Telegram chat"""
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
    
    def get_updates(self, offset: Optional[int] = None) -> Dict:
        """Get updates using polling"""
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        
        try:
            response = requests.get(url, params=params, timeout=35)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get updates: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def delete_webhook(self) -> Dict:
        """Delete webhook to use polling instead"""
        url = f"{self.base_url}/deleteWebhook"
        try:
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to delete webhook: {str(e)}")
            return {"ok": False, "error": str(e)}
    
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

def simple_chat_handler(message_text: str, user_id: str, username: str = None) -> str:
    """Simple chat handler with basic conversation logic"""
    
    text = message_text.lower().strip()
    
    # Handle commands
    if text.startswith('/start'):
        return (f"Hello! I'm a minimal Telegram bot. Nice to meet you, {username or user_id}! "
               "I can help you with basic tasks. Send /help to see what I can do.")
    
    elif text.startswith('/help'):
        return ("🤖 Available commands:\n\n"
               "/start - Start conversation\n"
               "/help - Show this help message\n"
               "/echo <text> - Echo your message\n"
               "/time - Get current time\n"
               "/weather - Ask about weather (placeholder)\n\n"
               "Or just send me any message and I'll respond!")
    
    elif text.startswith('/echo '):
        echo_text = message_text[6:]  # Remove '/echo '
        return f"📢 You said: {echo_text}"
    
    elif text.startswith('/time'):
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"🕐 Current time: {current_time}"
    
    elif text.startswith('/weather'):
        return ("🌤️ Weather feature is a placeholder. "
               "In a real implementation, this would connect to a weather API!")
    
    # Handle regular messages
    elif any(word in text for word in ["hello", "hi", "hey"]):
        return f"👋 Hello there! How can I help you today?"
    
    elif "how are you" in text:
        return "😊 I'm doing great! Thanks for asking. How about you?"
    
    elif "bye" in text or "goodbye" in text:
        return "👋 Goodbye! Have a great day!"
    
    elif "thank" in text:
        return "🙏 You're welcome! Is there anything else I can help you with?"
    
    elif "name" in text:
        return "🤖 My name is MinimalBot! I'm a simple Telegram bot built with Python."
    
    elif "help" in text:
        return ("💡 I can help you with:\n"
               "• Basic conversation\n"
               "• Echo messages (/echo)\n"
               "• Show time (/time)\n"
               "• Weather info (/weather)\n\n"
               "Send /help for all commands!")
    
    elif len(text) < 5:
        return "🤔 That's a short message! Can you tell me more?"
    
    elif len(text) > 100:
        return "📝 That's a long message! I appreciate the detail. What would you like me to help you with?"
    
    else:
        return (f"💬 I received your message: '{message_text}'\n\n"
               "This is a minimal bot without AI capabilities, but I can help with basic tasks! "
               "Send /help to see what I can do.")

def run_minimal_bot():
    """Run the minimal bot using polling"""
    
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set")
        logger.info("💡 Set it with: export TELEGRAM_BOT_TOKEN='your_bot_token_here'")
        return
    
    bot = MinimalTelegramBot(bot_token)
    
    # Test bot connection
    bot_info = bot.get_me()
    if not bot_info.get('ok'):
        logger.error(f"❌ Failed to connect to Telegram: {bot_info}")
        return
    
    bot_name = bot_info['result']['first_name']
    bot_username = bot_info['result']['username']
    logger.info(f"✅ Connected to Telegram bot: {bot_name} (@{bot_username})")
    
    # Delete any existing webhook to use polling
    logger.info("🔄 Setting up polling mode...")
    bot.delete_webhook()
    
    logger.info("🚀 Starting minimal Telegram bot (polling mode)...")
    logger.info("💡 Send /stop to the bot to exit")
    logger.info("📱 Send a message to @{} to start chatting!".format(bot_username))
    
    last_update_id = None
    message_count = 0
    
    try:
        while True:
            # Get updates
            updates = bot.get_updates(offset=last_update_id)
            
            if not updates.get('ok'):
                logger.error(f"❌ Failed to get updates: {updates}")
                time.sleep(5)  # Wait before retrying
                continue
            
            for update in updates.get('result', []):
                last_update_id = update['update_id'] + 1
                
                # Extract message data
                message = update.get('message', {})
                if not message:
                    continue
                
                chat_id = message['chat']['id']
                user_id = message['from']['id']
                username = message['from'].get('username')
                first_name = message['from'].get('first_name', 'User')
                text = message.get('text', '')
                
                message_count += 1
                logger.info(f"📨 Message #{message_count} from {username or first_name}: {text}")
                
                # Process message
                response = simple_chat_handler(text, user_id, username)
                
                # Send response
                result = bot.send_message(chat_id, response)
                if result.get('ok'):
                    logger.info(f"✅ Response sent to {username or first_name}")
                else:
                    logger.error(f"❌ Failed to send response: {result}")
                
                # Check for stop command
                if text.lower() == '/stop':
                    logger.info("🛑 Stop command received. Exiting...")
                    return
    
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Bot error: {str(e)}")

def test_bot_connection():
    """Test if the bot token is valid"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return False
    
    bot = MinimalTelegramBot(bot_token)
    bot_info = bot.get_me()
    
    if bot_info.get('ok'):
        result = bot_info['result']
        print(f"✅ Bot connection successful!")
        print(f"🤖 Name: {result['first_name']}")
        print(f"📱 Username: @{result['username']}")
        print(f"🆔 ID: {result['id']}")
        return True
    else:
        print(f"❌ Bot connection failed: {bot_info}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_bot_connection()
    else:
        run_minimal_bot() 