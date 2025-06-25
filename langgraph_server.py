from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the cloud_function directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloud_function'))

# Import the agent runner
from agent import run_agent_turn

app = Flask(__name__)
CORS(app)

# Global storage for local testing (in production this would be Firestore)
local_task_storage = {}
local_conversation_states = {}

@app.route('/process_message', methods=['POST'])
def handle_process_message():
    """HTTP endpoint to handle calls from the local Node.js email watcher."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract parameters for the agent
        user_input = data.get('user_input', '')
        user_email = data.get('user_email', '')
        task_json = data.get('task_json', {})
        previous_state = data.get('previous_state', None)
        
        logger.info(f"📨 Received message from {user_email}")
        logger.info(f"📋 Task: {task_json.get('taskTitle', 'Unknown')}")
        logger.info(f"💬 User input: {user_input[:100]}...")
        
        # Initialize task if this is the first message
        if not previous_state and task_json:
            task_id = task_json.get('taskId', f"{user_email}_{task_json.get('taskTitle', 'task')}_{datetime.now().isoformat()}")
            local_task_storage[task_id] = task_json
            local_conversation_states[task_id] = {
                'conversation_history': '',
                'is_complete': False,
                'user_email': user_email,
                'task_id': task_id
            }
            logger.info(f"🆕 Initialized new task: {task_id}")
        
        # Get conversation state
        task_id = task_json.get('taskId') if task_json else None
        if task_id and task_id in local_conversation_states:
            conversation_state = local_conversation_states[task_id]
        else:
            conversation_state = previous_state or {
                'conversation_history': '',
                'is_complete': False,
                'user_email': user_email
            }
        
        # Call the refactored agent function
        result = run_agent_turn(
            user_input=user_input,
            previous_state=conversation_state,
            user_email=user_email
        )
        
        # Update local storage
        if task_id:
            local_conversation_states[task_id] = {
                'conversation_history': result.get('conversation_history', ''),
                'is_complete': result.get('is_complete', False),
                'user_email': user_email,
                'task_id': task_id
            }
            logger.info(f"💾 Updated conversation state for task: {task_id}")
        
        # Add task info to response
        response_data = {
            **result,
            'task_json': task_json,
            'task_id': task_id
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in process_message endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

@app.route('/tasks', methods=['GET'])
def list_tasks():
    """List all local tasks for debugging."""
    return jsonify({
        "tasks": local_task_storage,
        "conversation_states": local_conversation_states
    })

@app.route('/clear', methods=['POST'])
def clear_local_data():
    """Clear local storage for testing."""
    global local_task_storage, local_conversation_states
    local_task_storage = {}
    local_conversation_states = {}
    return jsonify({"message": "Local storage cleared"})

if __name__ == '__main__':
    # Simplified startup for local testing, assuming single instance is managed manually.
    print("Starting LangGraph Test Server...")
    print("Server is available at: http://localhost:8000")
    print("Endpoints:")
    print("  POST /process_message - Process user responses")
    print("  GET /health - Health check")
    print("  GET /tasks - List all local tasks")
    print("  POST /clear - Clear local storage")
    print("\nPress Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=8000, debug=False) 