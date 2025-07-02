"""
Unified Messaging Abstraction Layer
Base classes and interfaces for different messaging providers (Telegram, Twilio, MessageCentral)
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages supported by the messaging system"""
    TEXT = "text"
    COMMAND = "command"
    MEDIA = "media"  # For future support

class MessageProvider(Enum):
    """Available messaging providers"""
    TELEGRAM = "telegram"
    TWILIO = "twilio"
    MESSAGECENTRAL = "messagecentral"

@dataclass
class IncomingMessage:
    """Standardized incoming message format across all providers"""
    # Core message data
    text: str
    user_id: str
    chat_id: str
    message_id: str
    
    # Provider-specific data
    provider: MessageProvider
    timestamp: str
    
    # User information
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    
    # Message metadata
    message_type: MessageType = MessageType.TEXT
    is_command: bool = False
    
    # Raw provider data (for debugging/future use)
    raw_data: Optional[Dict[str, Any]] = None

@dataclass
class OutgoingMessage:
    """Standardized outgoing message format"""
    text: str
    chat_id: str
    
    # Optional formatting
    parse_mode: Optional[str] = None  # "HTML", "Markdown", etc.
    
    # Optional metadata
    reply_to_message_id: Optional[str] = None
    
@dataclass
class MessageResult:
    """Result of sending a message"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None

class MessageProviderBase(ABC):
    """Abstract base class for all messaging providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the provider with configuration"""
        self.config = config
        self.provider_type = self._get_provider_type()
        
    @abstractmethod
    def _get_provider_type(self) -> MessageProvider:
        """Return the provider type"""
        pass
    
    @abstractmethod
    def send_message(self, message: OutgoingMessage) -> MessageResult:
        """Send a message through this provider"""
        pass
    
    @abstractmethod
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IncomingMessage]:
        """Parse raw webhook data into standardized IncomingMessage format"""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the provider is configured and ready to use"""
        pass
    
    def get_user_identifier(self, message: IncomingMessage) -> str:
        """Generate a consistent user identifier for state management"""
        provider_prefix = self.provider_type.value
        return f"{provider_prefix}_{message.user_id}"
    
    def supports_feature(self, feature: str) -> bool:
        """Check if provider supports a specific feature"""
        # Base implementation - override in subclasses
        basic_features = ["text_messages", "commands"]
        return feature in basic_features

class MessageManager:
    """Central coordinator for all messaging providers"""
    
    def __init__(self):
        self.providers: Dict[MessageProvider, MessageProviderBase] = {}
        self.default_provider: Optional[MessageProvider] = None
        
    def register_provider(self, provider: MessageProviderBase, is_default: bool = False):
        """Register a messaging provider"""
        provider_type = provider.provider_type
        self.providers[provider_type] = provider
        
        if is_default or not self.default_provider:
            self.default_provider = provider_type
            
        logger.info(f"Registered {provider_type.value} provider" + 
                   (" (default)" if is_default else ""))
    
    def get_provider(self, provider_type: MessageProvider) -> Optional[MessageProviderBase]:
        """Get a specific provider"""
        return self.providers.get(provider_type)
    
    def get_default_provider(self) -> Optional[MessageProviderBase]:
        """Get the default provider"""
        if self.default_provider:
            return self.providers.get(self.default_provider)
        return None
    
    def send_message(self, message: OutgoingMessage, 
                    provider_type: Optional[MessageProvider] = None) -> MessageResult:
        """Send a message using specified provider or default"""
        
        if provider_type:
            provider = self.get_provider(provider_type)
        else:
            provider = self.get_default_provider()
            
        if not provider:
            return MessageResult(
                success=False, 
                error=f"Provider {provider_type} not available"
            )
        
        try:
            return provider.send_message(message)
        except Exception as e:
            logger.error(f"Error sending message via {provider.provider_type.value}: {str(e)}")
            return MessageResult(
                success=False,
                error=f"Send error: {str(e)}"
            )
    
    def parse_webhook(self, raw_data: Dict[str, Any], 
                     provider_type: MessageProvider) -> Optional[IncomingMessage]:
        """Parse incoming webhook data"""
        provider = self.get_provider(provider_type)
        if not provider:
            logger.error(f"Provider {provider_type.value} not registered")
            return None
            
        try:
            return provider.parse_incoming_message(raw_data)
        except Exception as e:
            logger.error(f"Error parsing webhook from {provider_type.value}: {str(e)}")
            return None
    
    def get_healthy_providers(self) -> List[MessageProvider]:
        """Get list of healthy providers"""
        healthy = []
        for provider_type, provider in self.providers.items():
            try:
                if provider.is_healthy():
                    healthy.append(provider_type)
            except Exception as e:
                logger.error(f"Health check failed for {provider_type.value}: {str(e)}")
        return healthy
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {
            "default_provider": self.default_provider.value if self.default_provider else None,
            "providers": {}
        }
        
        for provider_type, provider in self.providers.items():
            try:
                is_healthy = provider.is_healthy()
                status["providers"][provider_type.value] = {
                    "healthy": is_healthy,
                    "features": [f for f in ["text_messages", "commands", "media"] 
                               if provider.supports_feature(f)]
                }
            except Exception as e:
                status["providers"][provider_type.value] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return status

# Global message manager instance
message_manager = MessageManager()