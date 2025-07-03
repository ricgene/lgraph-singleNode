"""
Telegram Provider Implementation
Handles Telegram Bot API integration using the unified messaging abstraction
"""

import os
import requests
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from .base import (
    MessageProviderBase, 
    MessageProvider, 
    IncomingMessage, 
    OutgoingMessage, 
    MessageResult,
    MessageType
)

logger = logging.getLogger(__name__)

class TelegramProvider(MessageProviderBase):
    """Telegram Bot API provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get('bot_token') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        
        if not self.bot_token:
            logger.warning("Telegram bot token not provided")
    
    def _get_provider_type(self) -> MessageProvider:
        return MessageProvider.TELEGRAM
    
    def send_message(self, message: OutgoingMessage) -> MessageResult:
        """Send a message via Telegram Bot API"""
        if not self.base_url:
            return MessageResult(
                success=False,
                error="Telegram bot token not configured"
            )
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': message.chat_id,
            'text': message.text
        }
        
        if message.parse_mode:
            payload['parse_mode'] = message.parse_mode
            
        if message.reply_to_message_id:
            payload['reply_to_message_id'] = message.reply_to_message_id
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result_data = response.json()
            
            if result_data.get('ok'):
                return MessageResult(
                    success=True,
                    message_id=str(result_data.get('result', {}).get('message_id')),
                    provider_response=result_data
                )
            else:
                return MessageResult(
                    success=False,
                    error=result_data.get('description', 'Unknown Telegram API error'),
                    provider_response=result_data
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram API request failed: {str(e)}")
            return MessageResult(
                success=False,
                error=f"API request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {str(e)}")
            return MessageResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Parse Telegram webhook update into IncomingMessage format"""
        try:
            # Extract message from Telegram update
            message_data = raw_data.get('message', {})
            if not message_data:
                logger.debug("No message in Telegram update")
                return None
            
            # Extract basic message info
            text = message_data.get('text', '')
            if not text:
                logger.debug("No text in Telegram message")
                return None
            
            # Extract user and chat info
            from_user = message_data.get('from', {})
            chat = message_data.get('chat', {})
            
            user_id = str(from_user.get('id', ''))
            chat_id = str(chat.get('id', ''))
            message_id = str(message_data.get('message_id', ''))
            
            if not user_id or not chat_id:
                logger.warning("Missing user_id or chat_id in Telegram message")
                return None
            
            # Determine message type
            is_command = text.startswith('/')
            message_type = MessageType.COMMAND if is_command else MessageType.TEXT
            
            # Create IncomingMessage
            return IncomingMessage(
                text=text,
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_id,
                provider=MessageProvider.TELEGRAM,
                timestamp=datetime.fromtimestamp(message_data.get('date', 0)).isoformat(),
                username=from_user.get('username'),
                first_name=from_user.get('first_name'),
                last_name=from_user.get('last_name'),
                message_type=message_type,
                is_command=is_command,
                raw_data=raw_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing Telegram message: {str(e)}")
            return None
    
    def is_healthy(self) -> bool:
        """Check if Telegram provider is configured and working"""
        if not self.bot_token or not self.base_url:
            return False
        
        try:
            # Test API connectivity with getMe
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            result = response.json()
            return result.get('ok', False)
            
        except Exception as e:
            logger.error(f"Telegram health check failed: {str(e)}")
            return False
    
    def supports_feature(self, feature: str) -> bool:
        """Check if Telegram provider supports a specific feature"""
        telegram_features = [
            "text_messages",
            "commands", 
            "markdown",
            "html",
            "reply_to_message",
            "inline_keyboards",  # Future feature
            "media"  # Future feature
        ]
        return feature in telegram_features
    
    def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Set the Telegram webhook URL"""
        if not self.base_url:
            return {"ok": False, "error": "Bot token not configured"}
        
        url = f"{self.base_url}/setWebhook"
        payload = {'url': webhook_url}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to set Telegram webhook: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information"""
        if not self.base_url:
            return {"ok": False, "error": "Bot token not configured"}
        
        url = f"{self.base_url}/getWebhookInfo"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Telegram webhook info: {str(e)}")
            return {"ok": False, "error": str(e)}