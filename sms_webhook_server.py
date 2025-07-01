#!/usr/bin/env python3
"""
SMS Webhook Server for Twilio Integration
Replaces email polling with instant SMS conversation
"""

import os
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from observability import get_logger
from messagecentral_sms import MessageCentralSMS

# Load environment variables
load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
USE_MOCK_TWILIO = os.getenv('USE_MOCK_TWILIO', 'true').lower() == 'true'
USE_MESSAGECENTRAL = os.getenv('USE_MESSAGECENTRAL', 'false').lower() == 'true'

# Initialize Flask app
app = Flask(__name__)

# Initialize observability
logger = get_logger("sms_webhook", "sms_webhook.log")

# Initialize SMS clients
twilio_client = None
messagecentral_client = None

if USE_MESSAGECENTRAL:
    messagecentral_client = MessageCentralSMS()
    logger.logger.info("📱 Using MessageCentral SMS")
elif not USE_MOCK_TWILIO and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    logger.logger.info("🔧 Using real Twilio client")
else:
    logger.logger.info("🔮 Using mock SMS for testing")

# Mock SMS database for testing
mock_sms_data = {}

class SMSConversationLoop:
    """SMS-based conversation loop using existing agent logic"""
    
    def __init__(self):
        # Import here to avoid circular dependencies
        sys.path.append(os.path.join(os.path.dirname(__file__), 'tests-new'))
        from local_agent_test_observable import ObservableLocalAgentFirestoreLoop
        self.agent_loop = ObservableLocalAgentFirestoreLoop()
    
    async def process_sms_message(self, phone_number: str, message_body: str, user_name: str = None):
        """Process an incoming SMS message using the agent loop"""
        
        # Use phone number as user email for agent loop
        user_email = f"{phone_number.replace('+', '').replace('-', '')}@sms.local"
        task_title = "SMS Conversation"
        user_first_name = user_name or f"User_{phone_number[-4:]}"
        
        with logger.trace_operation("sms_message_processing", {
            "phone_number": phone_number,
            "message_length": len(message_body),
            "user_email": user_email
        }):
            
            # Call the existing agent-firestore loop
            result = await self.agent_loop.run_conversation_turn(
                user_email=user_email,
                task_title=task_title,
                user_input=message_body,
                user_first_name=user_first_name
            )
            
            logger.logger.info(f"📱 SMS processed | turn={result.get('turn_count', 0)} | complete={result.get('is_complete', False)}")
            
            return result

class MockTwilioSMS:
    """Mock Twilio SMS for local testing"""
    
    @staticmethod
    def send_sms(to_number: str, message: str, from_number: str = None):
        """Mock SMS sending"""
        mock_sms_data[f"sms_{len(mock_sms_data)}"] = {
            "to": to_number,
            "from": from_number or TWILIO_PHONE_NUMBER,
            "body": message,
            "timestamp": datetime.now().isoformat(),
            "status": "delivered"
        }
        
        logger.logger.info(f"🔮 Mock SMS sent to {to_number}: '{message[:50]}...'")
        return {"sid": f"mock_sid_{len(mock_sms_data)}", "status": "sent"}

def send_sms_response(to_number: str, message: str):
    """Send SMS response via MessageCentral, Twilio, or mock"""
    
    # Try MessageCentral first if enabled
    if USE_MESSAGECENTRAL and messagecentral_client:
        try:
            with logger.trace_operation("messagecentral_sms_send", {
                "to_number": to_number,
                "message_length": len(message)
            }):
                result = messagecentral_client.send_sms(to_number, message)
                
                if result["status"] == "sent":
                    logger.logger.info(f"📤 MessageCentral SMS sent to {to_number} | ID: {result['sid']}")
                    return result
                else:
                    logger.logger.error(f"❌ MessageCentral SMS failed: {result.get('error', 'Unknown error')}")
                    # Fall through to other methods
                    
        except Exception as e:
            logger.logger.error(f"❌ MessageCentral SMS error: {str(e)}")
            # Fall through to other methods
    
    # Try Twilio if available
    if not USE_MOCK_TWILIO and twilio_client:
        try:
            with logger.trace_operation("twilio_sms_send", {
                "to_number": to_number,
                "message_length": len(message)
            }):
                message_obj = twilio_client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=to_number
                )
                
                logger.logger.info(f"📤 Twilio SMS sent to {to_number} | SID: {message_obj.sid}")
                return {"sid": message_obj.sid, "status": message_obj.status}
                
        except Exception as e:
            logger.logger.error(f"❌ Twilio SMS send failed: {str(e)}")
            # Fall through to mock
    
    # Fallback to mock SMS
    return MockTwilioSMS.send_sms(to_number, message)

# Initialize conversation loop
sms_loop = SMSConversationLoop()

@app.route('/sms/webhook', methods=['POST'])
def handle_incoming_sms():
    """Handle incoming SMS from Twilio webhook"""
    
    # Get SMS data from Twilio
    from_number = request.form.get('From', '')
    message_body = request.form.get('Body', '')
    to_number = request.form.get('To', '')
    
    logger.logger.info(f"📲 Incoming SMS from {from_number}: '{message_body[:50]}...'")
    
    try:
        # Process message with agent (run in event loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            sms_loop.process_sms_message(from_number, message_body)
        )
        
        # Get agent response
        agent_response = result.get('question', 'Thank you for your message!')
        
        # Send SMS response
        send_result = send_sms_response(from_number, agent_response)
        
        # Log conversation turn
        logger.log_conversation_turn(
            turn_number=result.get('turn_count', 0),
            user_input=message_body,
            agent_response=agent_response,
            metadata={
                "phone_number": from_number,
                "sms_sid": send_result.get('sid', ''),
                "is_complete": result.get('is_complete', False)
            }
        )
        
        # Return TwiML response (empty for webhook)
        resp = MessagingResponse()
        return str(resp)
        
    except Exception as e:
        logger.logger.error(f"❌ SMS webhook error: {str(e)}")
        
        # Send error response to user
        error_message = "Sorry, I encountered an issue. Please try again."
        send_sms_response(from_number, error_message)
        
        # Return empty TwiML
        resp = MessagingResponse()
        return str(resp)

@app.route('/sms/send', methods=['POST'])
def send_sms_endpoint():
    """Manual SMS sending endpoint for testing"""
    
    data = request.get_json()
    to_number = data.get('to', '')
    message = data.get('message', '')
    
    if not to_number or not message:
        return jsonify({"error": "Missing 'to' or 'message'"}), 400
    
    result = send_sms_response(to_number, message)
    
    return jsonify({
        "success": True,
        "sid": result.get('sid', ''),
        "status": result.get('status', ''),
        "message": f"SMS sent to {to_number}"
    })

@app.route('/sms/mock', methods=['POST'])
def simulate_incoming_sms():
    """Simulate incoming SMS for testing without Twilio"""
    
    data = request.get_json()
    from_number = data.get('from', '+1234567890')
    message_body = data.get('message', 'Hello')
    
    logger.logger.info(f"🔮 Simulating SMS from {from_number}: '{message_body}'")
    
    try:
        # Process with agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            sms_loop.process_sms_message(from_number, message_body)
        )
        
        agent_response = result.get('question', 'Thank you for your message!')
        
        # Mock send response
        send_result = MockTwilioSMS.send_sms(from_number, agent_response)
        
        return jsonify({
            "success": True,
            "conversation": {
                "user_input": message_body,
                "agent_response": agent_response,
                "turn_count": result.get('turn_count', 0),
                "is_complete": result.get('is_complete', False)
            },
            "sms_sent": send_result
        })
        
    except Exception as e:
        logger.logger.error(f"❌ Mock SMS error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/sms/status', methods=['GET'])
def sms_status():
    """Get SMS system status"""
    
    return jsonify({
        "status": "running",
        "sms_provider": "messagecentral" if USE_MESSAGECENTRAL else ("twilio" if twilio_client else "mock"),
        "messagecentral_enabled": USE_MESSAGECENTRAL,
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
        "mock_mode": USE_MOCK_TWILIO,
        "phone_number": TWILIO_PHONE_NUMBER,
        "mock_sms_count": len(mock_sms_data)
    })

@app.route('/sms/mock-data', methods=['GET'])
def get_mock_sms_data():
    """Get mock SMS data for testing"""
    return jsonify(mock_sms_data)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "sms_webhook_server"
    })

if __name__ == '__main__':
    logger.logger.info("🚀 Starting SMS Webhook Server")
    logger.logger.info(f"📱 MessageCentral enabled: {USE_MESSAGECENTRAL}")
    logger.logger.info(f"🔧 Twilio configured: {bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)}")
    logger.logger.info(f"🔮 Mock mode: {USE_MOCK_TWILIO}")
    logger.logger.info(f"📱 Phone number: {TWILIO_PHONE_NUMBER}")
    
    # Run Flask server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )