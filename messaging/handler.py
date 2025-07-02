"""
Unified Message Handler
Central handler that processes messages from any provider and integrates with LangGraph
"""

import os
import sys
import json
import logging
import requests
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
        """Process user input through LangGraph agent"""
        try:
            # Create unique user identifier
            user_identifier = f"{message.provider.value}_{message.user_id}"
            
            # Prepare the request payload for LangGraph
            payload = {
                "user_input": message.text,
                "user_email": f"{user_identifier}@{message.provider.value}.local",
                "task_json": {
                    "taskTitle": f"{message.provider.value.title()} Conversation",
                    "taskId": f"{message.provider.value}_{message.chat_id}_{datetime.now().isoformat()}",
                    "description": f"{message.provider.value.title()}-based conversation with LangGraph agent",
                    "category": "Communication"
                },
                "previous_state": None  # Will be handled by LangGraph's state management
            }
            
            # Call the LangGraph agent
            if self.langgraph_url and self.langgraph_key:
                headers = {
                    'Authorization': f'Bearer {self.langgraph_key}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    self.langgraph_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', 'I processed your message but had trouble generating a response.')
                else:
                    logger.error(f"LangGraph API error: {response.status_code} - {response.text}")
                    return "I'm having trouble processing your request right now. Please try again later."
            else:
                logger.error("LangGraph configuration missing")
                return "Bot configuration error. Please contact support."
                
        except Exception as e:
            logger.error(f"Error processing with LangGraph: {str(e)}")
            return "I encountered an error processing your message. Please try again."

# Global handler instance
message_handler = UnifiedMessageHandler()