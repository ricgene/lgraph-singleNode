"""
Twilio Provider Implementation
Handles Twilio SMS API integration using the unified messaging abstraction
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

class TwilioProvider(MessageProviderBase):
    """Twilio SMS API provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account_sid = config.get('account_sid') or os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = config.get('auth_token') or os.getenv('TWILIO_AUTH_TOKEN') 
        self.phone_number = config.get('phone_number') or os.getenv('TWILIO_PHONE_NUMBER')
        self.use_mock = config.get('use_mock', os.getenv('USE_MOCK_TWILIO', 'false').lower() == 'true')
        
        # Initialize Twilio client if credentials are available
        self.client = None
        if not self.use_mock and self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized")
            except ImportError:
                logger.error("Twilio library not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")
        elif self.use_mock:
            logger.info("Using mock Twilio for testing")
        else:
            logger.warning("Twilio credentials not provided")
    
    def _get_provider_type(self) -> MessageProvider:
        return MessageProvider.TWILIO
    
    def send_message(self, message: OutgoingMessage) -> MessageResult:
        """Send SMS via Twilio"""
        if self.use_mock:
            return self._send_mock_message(message)
        
        if not self.client or not self.phone_number:
            return MessageResult(
                success=False,
                error="Twilio not configured or phone number missing"
            )
        
        try:
            # For Twilio, chat_id is the recipient's phone number
            twilio_message = self.client.messages.create(
                body=message.text,
                from_=self.phone_number,
                to=message.chat_id
            )
            
            return MessageResult(
                success=True,
                message_id=twilio_message.sid,
                provider_response={
                    "sid": twilio_message.sid,
                    "status": twilio_message.status,
                    "date_created": str(twilio_message.date_created)
                }
            )
            
        except Exception as e:
            logger.error(f"Twilio send error: {str(e)}")
            return MessageResult(
                success=False,
                error=f"Twilio error: {str(e)}"
            )
    
    def _send_mock_message(self, message: OutgoingMessage) -> MessageResult:
        """Mock message sending for testing"""
        logger.info(f"MOCK SMS to {message.chat_id}: {message.text}")
        return MessageResult(
            success=True,
            message_id=f"mock_msg_{datetime.now().timestamp()}",
            provider_response={"mock": True, "to": message.chat_id}
        )
    
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Parse Twilio webhook data into IncomingMessage format"""
        try:
            # Twilio webhook sends form data, not JSON
            # Common fields: From, To, Body, MessageSid, etc.
            
            from_number = raw_data.get('From', '')
            to_number = raw_data.get('To', '')
            body = raw_data.get('Body', '')
            message_sid = raw_data.get('MessageSid', '')
            
            if not from_number or not body:
                logger.warning("Missing From number or Body in Twilio webhook")
                return None
            
            # Clean phone number (remove +1, etc.)
            user_id = from_number.replace('+', '').replace('-', '').replace(' ', '')
            chat_id = from_number  # Use full phone number as chat_id
            
            # SMS doesn't have commands in the same way as Telegram
            is_command = body.strip().lower().startswith('help') or body.strip().lower().startswith('stop')
            message_type = MessageType.COMMAND if is_command else MessageType.TEXT
            
            return IncomingMessage(
                text=body,
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_sid,
                provider=MessageProvider.TWILIO,
                timestamp=datetime.now().isoformat(),
                phone_number=from_number,
                message_type=message_type,
                is_command=is_command,
                raw_data=raw_data
            )
            
        except Exception as e:
            logger.error(f"Error parsing Twilio message: {str(e)}")
            return None
    
    def is_healthy(self) -> bool:
        """Check if Twilio provider is configured and working"""
        if self.use_mock:
            return True
            
        if not self.client:
            return False
        
        try:
            # Test by fetching account info
            account = self.client.api.accounts(self.account_sid).fetch()
            return account.status == 'active'
            
        except Exception as e:
            logger.error(f"Twilio health check failed: {str(e)}")
            return False
    
    def supports_feature(self, feature: str) -> bool:
        """Check if Twilio provider supports a specific feature"""
        twilio_features = [
            "text_messages",
            "commands",  # Basic command detection
            "phone_numbers",
            "delivery_status"  # Future feature
        ]
        return feature in twilio_features