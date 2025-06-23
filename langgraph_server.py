from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the cloud_function directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloud_function'))

# Import the agent runner
from agent import run_agent_turn

app = Flask(__name__)
CORS(app)

@app.route('/process_message', methods=['POST'])
def handle_process_message():
    """HTTP endpoint to handle calls from the local Node.js email watcher."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract parameters for the agent
        user_input = data.get('user_input', '')
        previous_state = data.get('previous_state', None)
        user_email = data.get('user_email', '')
        
        # Call the refactored agent function
        result = run_agent_turn(
            user_input=user_input,
            previous_state=previous_state,
            user_email=user_email
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in process_message endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    # Simplified startup for local testing, assuming single instance is managed manually.
    print("Starting LangGraph Test Server...")
    print("Server is available at: http://localhost:8000")
    print("Endpoints:")
    print("  POST /process_message - Process user responses")
    print("  GET /health - Health check")
    print("\nPress Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=8000, debug=False) 