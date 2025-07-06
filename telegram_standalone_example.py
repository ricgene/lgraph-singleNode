#!/usr/bin/env python3
"""
Standalone Telegram Bot Example
This shows how to use the Telegram function independently without the full unified system.

Requirements:
- TELEGRAM_BOT_TOKEN environment variable
- Firebase project (for user mapping)
- Optional: LANGGRAPH_DEPLOYMENT_URL and LANGGRAPH_API_KEY for AI responses
"""

import os
import requests
import json
import logging
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StandaloneTelegramBot:
    """Simple standalone Telegram bot without Firebase dependencies"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
    def send_message(self, chat_id: str, text: str) -> Dict:
        """Send a message to a Telegram chat"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_webhook_info(self) -> Dict:
        """Get current webhook information"""
        url = f"{self.base_url}/getWebhookInfo"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get webhook info: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def set_webhook(self, webhook_url: str) -> Dict:
        """Set webhook URL for the bot"""
        url = f"{self.base_url}/setWebhook"
        data = {"url": webhook_url}
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to set webhook: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def delete_webhook(self) -> Dict:
        """Delete webhook (use polling instead)"""
        url = f"{self.base_url}/deleteWebhook"
        try:
            response = requests.post(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to delete webhook: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_updates(self, offset: Optional[int] = None) -> Dict:
        """Get updates using polling (alternative to webhooks)"""
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get updates: {str(e)}")
            return {"ok": False, "error": str(e)}

def simple_message_handler(message_text: str, user_id: str, username: str = None) -> str:
    """Simple message handler without LangGraph dependency"""
    
    text = message_text.lower().strip()
    
    # Handle commands
    if text.startswith('/start'):
        return f"Hello! I'm a standalone Telegram bot. Nice to meet you, {username or user_id}!"
    
    elif text.startswith('/help'):
        return ("Available commands:\n"
               "/start - Start conversation\n"
               "/help - Show this help message\n"
               "/echo <text> - Echo your message\n"
               "\nOr just send me any message and I'll respond!")
    
    elif text.startswith('/echo '):
        echo_text = message_text[6:]  # Remove '/echo '
        return f"You said: {echo_text}"
    
    # Handle regular messages
    elif "hello" in text or "hi" in text:
        return f"Hello there! How can I help you today?"
    
    elif "how are you" in text:
        return "I'm doing great! Thanks for asking. How about you?"
    
    elif "bye" in text or "goodbye" in text:
        return "Goodbye! Have a great day!"
    
    else:
        return f"I received your message: '{message_text}'. This is a simple standalone bot without AI capabilities."

def run_standalone_bot():
    """Run the bot using polling (no webhook setup required)"""
    
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    bot = StandaloneTelegramBot(bot_token)
    
    # Delete any existing webhook to use polling
    logger.info("Setting up polling mode...")
    bot.delete_webhook()
    
    logger.info("Starting standalone Telegram bot (polling mode)...")
    logger.info("Send /stop to the bot to exit")
    
    last_update_id = None
    
    try:
        while True:
            # Get updates
            updates = bot.get_updates(offset=last_update_id)
            
            if not updates.get('ok'):
                logger.error(f"Failed to get updates: {updates}")
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
                text = message.get('text', '')
                
                logger.info(f"Received message from {username or user_id}: {text}")
                
                # Process message
                response = simple_message_handler(text, user_id, username)
                
                # Send response
                result = bot.send_message(chat_id, response)
                if result.get('ok'):
                    logger.info(f"Response sent to {username or user_id}")
                else:
                    logger.error(f"Failed to send response: {result}")
                
                # Check for stop command
                if text.lower() == '/stop':
                    logger.info("Stop command received. Exiting...")
                    return
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")

def webhook_example():
    """Example of how to set up webhook (requires public URL)"""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    bot = StandaloneTelegramBot(bot_token)
    
    # Example webhook URL (you would need a public HTTPS URL)
    webhook_url = "https://your-domain.com/telegram-webhook"
    
    logger.info(f"Setting webhook to: {webhook_url}")
    result = bot.set_webhook(webhook_url)
    
    if result.get('ok'):
        logger.info("Webhook set successfully!")
    else:
        logger.error(f"Failed to set webhook: {result}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "webhook":
        webhook_example()
    else:
        run_standalone_bot() 