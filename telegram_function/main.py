"""
Telegram Bot Google Cloud Function (Using Unified Messaging)
Handles incoming Telegram webhook updates using the unified messaging abstraction
"""

import os
import sys
import json
import logging
from typing import Dict, Optional

import functions_framework
from flask import Request

# Add messaging module to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import unified messaging system
from messaging import (
    MessageProvider,
    TelegramProvider,
    message_manager,
    message_handler
)

# Initialize Telegram provider
telegram_provider = None

def _initialize_telegram_provider():
    """Initialize Telegram provider if not already done"""
    global telegram_provider
    if not telegram_provider:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        if bot_token:
            telegram_provider = TelegramProvider({'bot_token': bot_token})
            message_manager.register_provider(telegram_provider, is_default=True)
            logger.info("Telegram provider initialized and registered")
        else:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
    return telegram_provider

@functions_framework.http
def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates using unified messaging"""
    
    # Only accept POST requests
    if request.method != 'POST':
        return {"error": "Only POST requests allowed"}, 405
    
    try:
        # Initialize Telegram provider
        provider = _initialize_telegram_provider()
        if not provider:
            return {"error": "Telegram provider not configured"}, 500
        
        # Get JSON data from request
        raw_data = request.get_json(silent=True)
        
        if not raw_data:
            logger.warning("No JSON data received")
            return {"error": "No data received"}, 400
        
        logger.info(f"Received Telegram webhook data")
        
        # Parse incoming message using unified system
        incoming_message = message_manager.parse_webhook(raw_data, MessageProvider.TELEGRAM)
        
        if not incoming_message:
            logger.info("No valid message found in webhook data")
            return {"status": "ignored", "reason": "no valid message"}, 200
        
        logger.info(f"Processing message from user {incoming_message.user_id}: {incoming_message.text}")
        
        # Process message using unified handler
        result = message_handler.process_message(incoming_message)
        
        if result.success:
            logger.info("Message processed and response sent successfully")
            return {"status": "success", "message_sent": True}, 200
        else:
            logger.error(f"Failed to process message: {result.error}")
            return {"error": "Failed to process message", "details": result.error}, 500
            
    except Exception as e:
        logger.error(f"Error handling Telegram webhook: {str(e)}")
        return {"error": "Internal server error"}, 500

@functions_framework.http
def telegram_setup(request: Request):
    """Setup Telegram webhook using unified messaging system"""
    
    if request.method != 'POST':
        return {"error": "Only POST requests allowed"}, 405
    
    try:
        # Initialize Telegram provider
        provider = _initialize_telegram_provider()
        if not provider:
            return {"error": "Telegram provider not configured"}, 500
        
        data = request.get_json(silent=True) or {}
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            return {"error": "webhook_url required"}, 400
        
        # Use provider's webhook management
        result = provider.set_webhook(webhook_url)
        
        return result, 200 if result.get('ok') else 500
        
    except Exception as e:
        logger.error(f"Error setting up webhook: {str(e)}")
        return {"error": "Internal server error"}, 500