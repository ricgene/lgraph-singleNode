#!/usr/bin/env python3
"""
Telegram Bot Integration for LangGraph Conversational Agent
Handles incoming Telegram messages and integrates with existing LangGraph agent
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

import requests
from flask import Flask, request, jsonify

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from observability import get_logger

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
LANGGRAPH_DEPLOYMENT_URL = os.getenv('LANGGRAPH_DEPLOYMENT_URL', '')
LANGGRAPH_API_KEY = os.getenv('LANGGRAPH_API_KEY', '')

# Initialize Flask app
app = Flask(__name__)

# Initialize observability  
logger = get_logger("telegram_bot", "telegram_bot.log")

class TelegramBot:
    """Telegram Bot API wrapper for sending messages and managing webhooks"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        
    def send_message(self, chat_id: str, text: str, parse_mode: str = None) -> Dict:
        """Send a message to a Telegram chat"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text
        }
        if parse_mode:
            payload['parse_mode'] = parse_mode
            
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.logger.error(f"❌ Failed to send Telegram message: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def set_webhook(self, webhook_url: str) -> Dict:
        """Set the webhook URL for receiving updates"""
        url = f"{self.base_url}/setWebhook"
        payload = {'url': webhook_url}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.logger.error(f"❌ Failed to set Telegram webhook: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_webhook_info(self) -> Dict:
        """Get current webhook information"""
        url = f"{self.base_url}/getWebhookInfo"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.logger.error(f"❌ Failed to get Telegram webhook info: {str(e)}")
            return {"ok": False, "error": str(e)}

# Initialize Telegram bot
telegram_bot = None
if TELEGRAM_BOT_TOKEN:
    telegram_bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    logger.logger.info("🤖 Telegram bot initialized")
else:
    logger.logger.warning("⚠️ TELEGRAM_BOT_TOKEN not set - bot will not function")

def process_with_langgraph(user_input: str, user_id: str, chat_id: str) -> str:
    """Process user input through LangGraph agent"""
    try:
        # Prepare the request payload for LangGraph
        payload = {
            "user_input": user_input,
            "user_email": f"telegram_{user_id}@telegram.local",  # Create unique identifier
            "task_json": {
                "taskTitle": "Telegram Conversation",
                "taskId": f"telegram_{chat_id}_{datetime.now().isoformat()}",
                "description": "Telegram-based conversation with LangGraph agent",
                "category": "Communication"
            },
            "previous_state": None  # Will be handled by LangGraph's state management
        }
        
        # Call the LangGraph agent
        if LANGGRAPH_DEPLOYMENT_URL and LANGGRAPH_API_KEY:
            headers = {
                'Authorization': f'Bearer {LANGGRAPH_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                LANGGRAPH_DEPLOYMENT_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'I processed your message but had trouble generating a response.')
            else:
                logger.logger.error(f"❌ LangGraph API error: {response.status_code} - {response.text}")
                return "I'm having trouble processing your request right now. Please try again later."
        else:
            logger.logger.error("❌ LangGraph configuration missing")
            return "Bot configuration error. Please contact support."
            
    except Exception as e:
        logger.logger.error(f"❌ Error processing with LangGraph: {str(e)}")
        return "I encountered an error processing your message. Please try again."

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Handle incoming Telegram webhook updates"""
    try:
        update = request.get_json()
        
        if not update:
            return jsonify({"error": "No data received"}), 400
        
        logger.logger.info(f"📨 Received Telegram update: {json.dumps(update, indent=2)}")
        
        # Extract message information
        message = update.get('message', {})
        if not message:
            # Could be edited message, inline query, etc. - ignore for now
            return jsonify({"status": "ignored", "reason": "no message"}), 200
        
        chat_id = message.get('chat', {}).get('id')
        user_id = message.get('from', {}).get('id')
        username = message.get('from', {}).get('username', 'unknown')
        text = message.get('text', '')
        
        if not chat_id or not text:
            return jsonify({"error": "Missing chat_id or text"}), 400
        
        logger.logger.info(f"👤 Message from @{username} (ID: {user_id}) in chat {chat_id}: {text}")
        
        # Handle special commands
        if text.startswith('/'):
            if text.startswith('/start'):
                response_text = ("Hello! I'm your AI assistant powered by LangGraph. "
                               "I can help you with various tasks and answer questions. "
                               "Just send me a message to get started!")
            elif text.startswith('/help'):
                response_text = ("Available commands:\n"
                               "/start - Start conversation\n"
                               "/help - Show this help message\n"
                               "\nOr just send me any message and I'll respond using AI!")
            else:
                response_text = "Unknown command. Use /help to see available commands."
        else:
            # Process regular message through LangGraph
            response_text = process_with_langgraph(text, str(user_id), str(chat_id))
        
        # Send response back to Telegram
        if telegram_bot:
            result = telegram_bot.send_message(str(chat_id), response_text)
            if result.get('ok'):
                logger.logger.info(f"✅ Response sent successfully")
                return jsonify({"status": "success", "message_sent": True}), 200
            else:
                logger.logger.error(f"❌ Failed to send response: {result}")
                return jsonify({"error": "Failed to send response"}), 500
        else:
            logger.logger.error("❌ Telegram bot not initialized")
            return jsonify({"error": "Bot not configured"}), 500
            
    except Exception as e:
        logger.logger.error(f"❌ Error handling Telegram webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/telegram/setup', methods=['POST'])
def setup_webhook():
    """Setup Telegram webhook (for manual configuration)"""
    try:
        if not telegram_bot:
            return jsonify({"error": "Bot not configured"}), 500
        
        webhook_url = request.json.get('webhook_url', TELEGRAM_WEBHOOK_URL)
        if not webhook_url:
            return jsonify({"error": "webhook_url required"}), 400
        
        result = telegram_bot.set_webhook(webhook_url)
        return jsonify(result), 200 if result.get('ok') else 500
        
    except Exception as e:
        logger.logger.error(f"❌ Error setting up webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/telegram/info', methods=['GET'])
def webhook_info():
    """Get current webhook information"""
    try:
        if not telegram_bot:
            return jsonify({"error": "Bot not configured"}), 500
        
        result = telegram_bot.get_webhook_info()
        return jsonify(result), 200 if result.get('ok') else 500
        
    except Exception as e:
        logger.logger.error(f"❌ Error getting webhook info: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/telegram/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot_configured": bool(telegram_bot and TELEGRAM_BOT_TOKEN),
        "langgraph_configured": bool(LANGGRAPH_DEPLOYMENT_URL and LANGGRAPH_API_KEY),
        "timestamp": datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    logger.logger.info("🚀 Starting Telegram Bot server...")
    
    # Log configuration status
    if telegram_bot:
        logger.logger.info("✅ Telegram bot configured")
        if TELEGRAM_WEBHOOK_URL:
            logger.logger.info(f"🌐 Webhook URL: {TELEGRAM_WEBHOOK_URL}")
        else:
            logger.logger.warning("⚠️ TELEGRAM_WEBHOOK_URL not set - manual webhook setup required")
    else:
        logger.logger.error("❌ Telegram bot not configured - check TELEGRAM_BOT_TOKEN")
    
    if LANGGRAPH_DEPLOYMENT_URL and LANGGRAPH_API_KEY:
        logger.logger.info("✅ LangGraph integration configured")
    else:
        logger.logger.error("❌ LangGraph not configured - check LANGGRAPH_DEPLOYMENT_URL and LANGGRAPH_API_KEY")
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)