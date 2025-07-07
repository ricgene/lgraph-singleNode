#!/usr/bin/env python3
"""
Telegram API Debug Tool
Helps diagnose and fix Telegram API 400 Bad Request errors

Common causes:
1. Invalid chat_id format
2. Bot not added to chat/group
3. Bot blocked by user
4. Invalid message content
5. Rate limiting
"""

import os
import requests
import json
import logging
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramDebugger:
    """Debug Telegram API issues"""
    
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
    
    def test_send_message(self, chat_id: str, text: str = "Test message") -> Dict:
        """Test sending a message and get detailed error info"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text
        }
        
        logger.info(f"Testing send message to chat_id: {chat_id}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Success! Response: {json.dumps(result, indent=2)}")
                return result
            else:
                logger.error(f"❌ HTTP {response.status_code}")
                logger.error(f"Response text: {response.text}")
                
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                    return error_data
                except:
                    logger.error(f"Raw response: {response.text}")
                    return {"ok": False, "error": f"HTTP {response.status_code}: {response.text}"}
                    
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_chat(self, chat_id: str) -> Dict:
        """Get information about a specific chat"""
        url = f"{self.base_url}/getChat"
        params = {"chat_id": chat_id}
        
        logger.info(f"Getting chat info for chat_id: {chat_id}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Chat info: {json.dumps(result, indent=2)}")
                return result
            else:
                logger.error(f"❌ HTTP {response.status_code}")
                logger.error(f"Response text: {response.text}")
                
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                    return error_data
                except:
                    logger.error(f"Raw response: {response.text}")
                    return {"ok": False, "error": f"HTTP {response.status_code}: {response.text}"}
                    
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_updates(self, limit: int = 10) -> Dict:
        """Get recent updates to see valid chat_ids"""
        url = f"{self.base_url}/getUpdates"
        params = {"limit": limit}
        
        logger.info(f"Getting recent updates (limit: {limit})")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                updates = result.get('result', [])
                logger.info(f"✅ Found {len(updates)} updates")
                
                chat_ids = set()
                for update in updates:
                    message = update.get('message', {})
                    if message:
                        chat = message.get('chat', {})
                        chat_id = chat.get('id')
                        chat_type = chat.get('type')
                        title = chat.get('title', '')
                        username = chat.get('username', '')
                        first_name = chat.get('first_name', '')
                        
                        if chat_id:
                            chat_ids.add(chat_id)
                            logger.info(f"  Chat ID: {chat_id} (Type: {chat_type})")
                            if chat_type == 'private':
                                display_name = f"{first_name} {username or ''}".strip()
                                logger.info(f"    User: {display_name}")
                            elif chat_type in ['group', 'supergroup']:
                                logger.info(f"    Group: {title} (@{username})")
                            elif chat_type == 'channel':
                                logger.info(f"    Channel: {title} (@{username})")
                
                logger.info(f"📊 Unique chat IDs found: {list(chat_ids)}")
                return result
            else:
                logger.error(f"❌ Failed to get updates: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return {"ok": False, "error": str(e)}

def diagnose_400_error(bot_token: str, chat_id: str, message_text: str = "Test message"):
    """Comprehensive diagnosis of 400 Bad Request error"""
    
    logger.info("🔍 Diagnosing Telegram API 400 Bad Request Error")
    logger.info("=" * 60)
    
    debugger = TelegramDebugger(bot_token)
    
    # 1. Check bot status
    logger.info("1️⃣ Checking bot status...")
    bot_info = debugger.get_me()
    if not bot_info.get('ok'):
        logger.error("❌ Bot token is invalid or bot is not accessible")
        return
    
    bot_name = bot_info['result']['first_name']
    bot_username = bot_info['result']['username']
    logger.info(f"✅ Bot: {bot_name} (@{bot_username})")
    
    # 2. Check chat_id format and validity
    logger.info("\n2️⃣ Checking chat_id format and validity...")
    logger.info(f"Chat ID: {chat_id} (Type: {type(chat_id)})")
    
    # Validate chat_id format
    try:
        chat_id_int = int(chat_id)
        if chat_id_int > 0:
            logger.info("✅ Chat ID is positive (private chat)")
        elif str(chat_id_int).startswith("-100"):
            logger.info("✅ Chat ID is channel format")
        else:
            logger.info("✅ Chat ID is group format")
    except ValueError:
        logger.error("❌ Chat ID is not a valid integer")
        return
    
    # 3. Try to get chat information
    logger.info("\n3️⃣ Getting chat information...")
    chat_info = debugger.get_chat(chat_id)
    
    if chat_info.get('ok'):
        chat_data = chat_info['result']
        chat_type = chat_data.get('type')
        logger.info(f"✅ Chat exists and is accessible")
        logger.info(f"   Type: {chat_type}")
        logger.info(f"   Title: {chat_data.get('title', 'N/A')}")
        logger.info(f"   Username: @{chat_data.get('username', 'N/A')}")
        
        # Check if bot is member/admin
        if chat_type in ['group', 'supergroup']:
            bot_member = chat_data.get('all_members_are_administrators', False)
            logger.info(f"   Bot member status: {bot_member}")
    else:
        error_code = chat_info.get('error_code')
        description = chat_info.get('description', '')
        
        logger.error(f"❌ Cannot access chat: {description}")
        
        if error_code == 400:
            logger.error("   This suggests the chat_id format is invalid")
        elif error_code == 403:
            logger.error("   Bot is not a member of this chat/group")
        elif error_code == 404:
            logger.error("   Chat not found - user may have blocked the bot")
        
        return
    
    # 4. Test sending message
    logger.info("\n4️⃣ Testing message sending...")
    send_result = debugger.test_send_message(chat_id, message_text)
    
    if send_result.get('ok'):
        logger.info("✅ Message sent successfully!")
        return
    else:
        error_code = send_result.get('error_code')
        description = send_result.get('description', '')
        
        logger.error(f"❌ Failed to send message: {description}")
        
        # Provide specific solutions based on error
        if error_code == 400:
            if "chat not found" in description.lower():
                logger.error("   Solution: User may have blocked the bot or chat doesn't exist")
            elif "message is not modified" in description.lower():
                logger.error("   Solution: Message content is identical to previous message")
            elif "message text is empty" in description.lower():
                logger.error("   Solution: Message text is empty or invalid")
            else:
                logger.error("   Solution: Check message format and content")
        elif error_code == 403:
            logger.error("   Solution: Bot is not a member of this chat/group")
        elif error_code == 429:
            logger.error("   Solution: Rate limit exceeded - wait before sending more messages")
    
    # 5. Show recent valid chat_ids
    logger.info("\n5️⃣ Recent valid chat IDs for reference...")
    debugger.get_updates(5)

def check_common_issues():
    """Check for common configuration issues"""
    
    logger.info("🔧 Checking for common configuration issues...")
    logger.info("=" * 50)
    
    # Check environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set")
        return False
    
    logger.info("✅ TELEGRAM_BOT_TOKEN is set")
    
    # Check token format
    if not bot_token.count(':') == 1:
        logger.error("❌ Bot token format appears invalid (should be 'number:letters')")
        return False
    
    logger.info("✅ Bot token format looks correct")
    
    # Test basic connectivity
    debugger = TelegramDebugger(bot_token)
    bot_info = debugger.get_me()
    
    if not bot_info.get('ok'):
        logger.error("❌ Bot token is invalid or bot is not accessible")
        return False
    
    logger.info("✅ Bot is accessible and token is valid")
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python telegram_debug_tool.py check")
        print("  python telegram_debug_tool.py diagnose <chat_id> [message]")
        print("  python telegram_debug_tool.py updates")
        print("")
        print("Examples:")
        print("  python telegram_debug_tool.py check")
        print("  python telegram_debug_tool.py diagnose 123456789")
        print("  python telegram_debug_tool.py diagnose 123456789 'Hello world'")
        print("  python telegram_debug_tool.py updates")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        check_common_issues()
    
    elif command == "diagnose":
        if len(sys.argv) < 3:
            print("❌ Please provide a chat_id")
            sys.exit(1)
        
        chat_id = sys.argv[2]
        message = sys.argv[3] if len(sys.argv) > 3 else "Test message"
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN environment variable not set")
            sys.exit(1)
        
        diagnose_400_error(bot_token, chat_id, message)
    
    elif command == "updates":
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN environment variable not set")
            sys.exit(1)
        
        debugger = TelegramDebugger(bot_token)
        debugger.get_updates()
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1) 