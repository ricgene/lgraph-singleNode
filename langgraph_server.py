from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import sys

# Add the current directory to Python path so we can import oneNodeRemMem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the process_message function from oneNodeRemMem
from oneNodeRemMem import process_message

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

@app.route('/process_message', methods=['POST'])
def handle_process_message():
    """HTTP endpoint to handle LangGraph process_message calls from Node.js"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract parameters
        user_input = data.get('user_input', '')
        previous_state = data.get('previous_state', None)
        user_email = data.get('user_email', '')
        
        # Call the LangGraph process_message function
        result = process_message({
            'user_input': user_input,
            'previous_state': previous_state,
            'user_email': user_email
        })
        
        # Return the result as JSON
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in process_message endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "langgraph-email-integration"})

@app.route('/start_conversation', methods=['POST'])
def start_conversation():
    """Endpoint to start a new conversation with a user"""
    try:
        data = request.get_json()
        user_email = data.get('user_email', '')
        
        if not user_email:
            return jsonify({"error": "user_email is required"}), 400
        
        # Start a new conversation (empty user input)
        result = process_message({
            'user_input': '',
            'previous_state': None,
            'user_email': user_email
        })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in start_conversation endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting LangGraph Email Integration Server...")
    print("Server will be available at: http://localhost:8000")
    print("Endpoints:")
    print("  POST /process_message - Process user responses")
    print("  POST /start_conversation - Start new conversation")
    print("  GET /health - Health check")
    print("\nPress Ctrl+C to stop the server")
    
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False) 