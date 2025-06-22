from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import sys
import logging
import socket
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PID_FILE = "/tmp/langgraph_server.pid"

# Add the current directory to Python path so we can import oneNodeRemMem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the process_message function from oneNodeRemMem
from oneNodeRemMem import process_message

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True

def create_pid_file():
    """Create PID file to track running instance"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID file created: {PID_FILE}")
    except Exception as e:
        logger.error(f"Failed to create PID file: {e}")

def remove_pid_file():
    """Remove PID file on exit"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info("PID file removed")
    except Exception as e:
        logger.error(f"Failed to remove PID file: {e}")

def check_single_instance():
    """Ensure only one instance of the server is running"""
    # Check if PID file exists and process is running
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Check if process is still running
            os.kill(pid, 0)  # This will raise OSError if process doesn't exist
            logger.error(f"Server already running with PID {pid}")
            logger.error("Please stop the existing server before starting a new one.")
            sys.exit(1)
        except (ValueError, OSError):
            # PID file exists but process is dead, remove stale file
            remove_pid_file()
    
    # Check if port is in use
    if is_port_in_use(8000):
        logger.error("Port 8000 is already in use. Another instance may be running.")
        logger.error("Please stop the existing server before starting a new one.")
        sys.exit(1)
    
    logger.info("Port 8000 is available. Starting server...")
    create_pid_file()

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
    check_single_instance()
    print("Starting LangGraph Email Integration Server...")
    print("Server will be available at: http://localhost:8000")
    print("Endpoints:")
    print("  POST /process_message - Process user responses")
    print("  POST /start_conversation - Start new conversation")
    print("  GET /health - Health check")
    print("\nPress Ctrl+C to stop the server")
    
    atexit.register(remove_pid_file)
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False) 