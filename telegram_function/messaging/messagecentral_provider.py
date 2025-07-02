"""
MessageCentral Provider Implementation
Handles MessageCentral SMS API integration using the unified messaging abstraction
"""

import os
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

class MessageCentralProvider(MessageProviderBase):
    """MessageCentral SMS API provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.customer_id = config.get('customer_id') or os.getenv('MC_CUSTOMER_ID')
        self.password = config.get('password') or os.getenv('MC_PASSWORD')
        self.password_base64 = config.get('password_base64') or os.getenv('MC_PASSWORD_BASE64')
        self.sender_id = config.get('sender_id', 'UTOMOB')
        self.base_url = "https://cpaas.messagecentral.com"
        self.token = None
        
        # Import MessageCentral client if available
        self.mc_client = None
        try:
            import sys
            import os
            # Add parent directory to path to import messagecentral_sms
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent_dir not in sys.path:
                sys.path.append(parent_dir)
            
            from messagecentral_sms import MessageCentralSMS
            self.mc_client = MessageCentralSMS()
            logger.info("MessageCentral client initialized")
        except ImportError:
            logger.warning("MessageCentral SMS module not available")
        except Exception as e:
            logger.error(f"Failed to initialize MessageCentral client: {str(e)}")
    
    def _get_provider_type(self) -> MessageProvider:
        return MessageProvider.MESSAGECENTRAL
    
    def send_message(self, message: OutgoingMessage) -> MessageResult:
        """Send SMS via MessageCentral"""
        if not self.mc_client:
            return MessageResult(
                success=False,
                error="MessageCentral client not available"
            )
        
        try:
            # For MessageCentral, chat_id is the recipient's phone number
            result = self.mc_client.send_sms(
                to_number=message.chat_id,
                message=message.text,
                sender_id=self.sender_id
            )
            
            # MessageCentral returns a dict with sid, status, etc.
            if result.get('status') == 'sent' or result.get('sid'):
                return MessageResult(
                    success=True,
                    message_id=result.get('sid'),
                    provider_response=result
                )
            else:
                return MessageResult(
                    success=False,
                    error=result.get('error', 'Unknown MessageCentral error'),
                    provider_response=result
                )
            
        except Exception as e:
            logger.error(f"MessageCentral send error: {str(e)}")
            return MessageResult(
                success=False,
                error=f"MessageCentral error: {str(e)}"
            )
    
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Parse MessageCentral webhook data into IncomingMessage format"""
        try:
            # MessageCentral webhook format (adjust based on their webhook spec)
            # This is a placeholder - you'll need to adjust based on actual webhook format
            
            from_number = raw_data.get('from', raw_data.get('mobileNumber', ''))
            to_number = raw_data.get('to', '')
            text = raw_data.get('message', raw_data.get('text', ''))
            message_id = raw_data.get('messageId', raw_data.get('id', ''))
            
            if not from_number or not text:
                logger.warning("Missing from number or text in MessageCentral webhook")
                return None
            
            # Clean phone number
            user_id = from_number.replace('+', '').replace('-', '').replace(' ', '')
            chat_id = from_number  # Use full phone number as chat_id
            
            # SMS doesn't have commands in the same way as Telegram
            is_command = text.strip().lower().startswith('help') or text.strip().lower().startswith('stop')
            message_type = MessageType.COMMAND if is_command else MessageType.TEXT
            
            return IncomingMessage(
                text=text,
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_id,
                provider=MessageProvider.MESSAGECENTRAL,
                timestamp=datetime.now().isoformat(),
                phone_number=from_number,
                message_type=message_type,
                is_command=is_command,
                raw_data=raw_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing MessageCentral message: {str(e)}")
            return None
    
    def is_healthy(self) -> bool:
        """Check if MessageCentral provider is configured and working"""
        if not self.mc_client:
            return False
            
        if not self.customer_id or not (self.password or self.password_base64):
            return False
        
        try:
            # Test by generating a token
            return self.mc_client.generate_token()
            
        except Exception as e:
            logger.error(f"MessageCentral health check failed: {str(e)}")
            return False
    
    def supports_feature(self, feature: str) -> bool:
        """Check if MessageCentral provider supports a specific feature"""
        messagecentral_features = [
            "text_messages",
            "commands",  # Basic command detection
            "phone_numbers",
            "international_sms",
            "delivery_reports"  # Future feature
        ]
        return feature in messagecentral_features