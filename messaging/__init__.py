"""
Unified Messaging System
Abstracts Telegram, Twilio, and MessageCentral into a common interface
"""

from .base import (
    MessageProvider,
    MessageType,
    IncomingMessage,
    OutgoingMessage,
    MessageResult,
    MessageProviderBase,
    MessageManager,
    message_manager
)

from .telegram_provider import TelegramProvider
from .twilio_provider import TwilioProvider
from .messagecentral_provider import MessageCentralProvider

__all__ = [
    'MessageProvider',
    'MessageType', 
    'IncomingMessage',
    'OutgoingMessage',
    'MessageResult',
    'MessageProviderBase',
    'MessageManager',
    'message_manager',
    'TelegramProvider',
    'TwilioProvider',
    'MessageCentralProvider'
]