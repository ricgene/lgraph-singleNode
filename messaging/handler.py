"""
Unified Message Handler
Central handler that processes messages from any provider and integrates with LangGraph
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from .base import (
    MessageProvider,
    IncomingMessage,
    OutgoingMessage,
    MessageResult,
    message_manager
)

# Add parent directory to path for LangGraph integration
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

logger = logging.getLogger(__name__)

class UnifiedMessageHandler:
    """Central handler for processing messages from any provider"""
    
    def __init__(self):
        self.langgraph_url = os.getenv('LANGGRAPH_DEPLOYMENT_URL')
        self.langgraph_key = os.getenv('LANGGRAPH_API_KEY')
        self.langgraph_client = None
        
        # Initialize LangGraph client if credentials are available
        if self.langgraph_url and self.langgraph_key:
            try:
                from langgraph_sdk import get_sync_client
                self.langgraph_client = get_sync_client(url=self.langgraph_url, api_key=self.langgraph_key)
                logger.info("LangGraph sync client initialized")
            except ImportError:
                logger.error("langgraph_sdk not installed")
            except Exception as e:
                logger.error(f"Failed to initialize LangGraph client: {str(e)}")
        
    def process_message(self, incoming_message: IncomingMessage) -> MessageResult:
        """Process an incoming message and send response"""
        
        try:
            # Handle special commands first
            if incoming_message.is_command:
                response_text = self._handle_command(incoming_message)
            else:
                # Process through LangGraph
                response_text = self._process_with_langgraph(incoming_message)
            
            # Send response back through the same provider
            outgoing_message = OutgoingMessage(
                text=response_text,
                chat_id=incoming_message.chat_id
            )
            
            result = message_manager.send_message(
                outgoing_message, 
                provider_type=incoming_message.provider
            )
            
            if result.success:
                logger.info(f"Response sent successfully via {incoming_message.provider.value}")
            else:
                logger.error(f"Failed to send response: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return MessageResult(
                success=False,
                error=f"Processing error: {str(e)}"
            )
    
    def _handle_command(self, message: IncomingMessage) -> str:
        """Handle special commands"""
        text = message.text.lower().strip()
        
        if text.startswith('/start') or text.startswith('start'):
            if message.provider == MessageProvider.TELEGRAM:
                return ("Hello! I'm your AI assistant powered by LangGraph. "
                       "I can help you with various tasks and answer questions. "
                       "Just send me a message to get started!")
            else:
                return ("Hello! I'm your AI assistant. Send me a message and I'll help you with various tasks.")
        
        elif text.startswith('/help') or text.startswith('help'):
            if message.provider == MessageProvider.TELEGRAM:
                return ("Available commands:\n"
                       "/start - Start conversation\n"
                       "/help - Show this help message\n"
                       "\nOr just send me any message and I'll respond using AI!")
            else:
                return ("Commands: HELP, STOP. Or just send me any message and I'll respond using AI!")
        
        elif text.startswith('stop'):
            return "You can restart the conversation anytime by sending a new message."
        
        else:
            return "Unknown command. Send HELP to see available commands, or just send me a regular message."
    
    def _process_with_langgraph(self, message: IncomingMessage) -> str:
        """Process user input through LangGraph agent using SDK"""
        try:
            # For now, return a simple response while we debug the SDK
            # TODO: Replace with working LangGraph SDK pattern
            
            logger.info(f"Processing message: {message.text}")
            
            # Simple response for testing
            if "hello" in message.text.lower():
                return "Hello! I'm your AI assistant. I'm currently being configured to use LangGraph. How can I help you today?"
            elif "test" in message.text.lower():
                return "Test message received! The Telegram integration is working. LangGraph processing is being debugged."
            else:
                return f"I received your message: '{message.text}'. I'm currently being configured to provide AI-powered responses through LangGraph."
                
        except Exception as e:
            logger.error(f"Error processing with LangGraph SDK: {str(e)}")
            return "I encountered an error processing your message. Please try again."

# Global handler instance
message_handler = UnifiedMessageHandler()