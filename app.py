from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from agent import graph
from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only - restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory session storage (replace with database in production)
sessions: Dict[str, Dict[str, Any]] = {}

def create_initial_state() -> Dict[str, Any]:
    """Create a new initial state for the agent"""
    logger.debug("Creating initial state")
    state = {
        "messages": [AIMessage(content="Hello! I'm here to help you with your needs. Could you please tell me what you're looking for?")],
        "internal_memory": {},
        "current_question": 0,
        "sub_question_context": None,
        "sub_question_count": 0,
        "answers": {},
        "questioning_complete": False,
        "outcome": "needs_more_info",
        "waiting_for_user": False
    }
    logger.debug(f"Initial state created: {state}")
    return state

def serialize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Convert state to JSON-serializable format"""
    serialized = state.copy()
    # Convert messages to serializable format
    serialized["messages"] = [
        {
            "type": "human" if isinstance(msg, HumanMessage) else "ai",
            "content": msg.content
        }
        for msg in state["messages"]
    ]
    return serialized

def deserialize_state(serialized: Dict[str, Any]) -> Dict[str, Any]:
    """Convert serialized state back to agent-compatible format"""
    state = serialized.copy()
    # Convert messages back to LangChain message objects
    state["messages"] = [
        HumanMessage(content=msg["content"]) if msg["type"] == "human"
        else AIMessage(content=msg["content"])
        for msg in serialized["messages"]
    ]
    return state

@app.get("/")
def read_root():
    return {"message": "LangGraph Agent API is running. Connect to the WebSocket at /chat"}

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection request received")
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info(f"New connection established with session ID: {session_id}")
    
    try:
        # Initialize new session with greeting
        initial_state = create_initial_state()
        sessions[session_id] = initial_state
        logger.debug(f"Session {session_id} initialized with state: {initial_state}")
        
        # Send the initial greeting message immediately
        if initial_state["messages"]:
            initial_message = {
                "type": "message", 
                "content": initial_state["messages"][-1].content,
                "session_id": session_id
            }
            logger.info(f"Sending initial message: {initial_message}")
            await websocket.send_text(json.dumps(initial_message))
        else:
            logger.warning("No initial message to send!")
        
        # Function to handle streaming responses
        async def stream_handler(chunk):
            try:
                logger.debug(f"Streaming chunk: {chunk}")
                await websocket.send_text(json.dumps({
                    "type": "chunk", 
                    "content": chunk,
                    "session_id": session_id
                }))
            except Exception as e:
                logger.error(f"Error sending chunk: {e}")
        
        # Main interaction loop
        while True:
            try:
                # Receive message from user
                logger.debug("Waiting for user message...")
                data = await websocket.receive_text()
                logger.info(f"Received message: {data}")
                
                message_data = json.loads(data)
                user_message = message_data.get("content", "")
                received_session_id = message_data.get("session_id")
                
                logger.debug(f"Parsed message - content: {user_message}, session_id: {received_session_id}")
                
                # If no session ID provided, create a new session
                if not received_session_id:
                    received_session_id = str(uuid.uuid4())
                    logger.info(f"No session ID provided, creating new session: {received_session_id}")
                    sessions[received_session_id] = create_initial_state()
                
                # Validate session
                if received_session_id not in sessions:
                    logger.error(f"Invalid session ID: {received_session_id}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": "Invalid session ID"
                    }))
                    continue
                
                # Get current state
                current_state = sessions[received_session_id]
                logger.debug(f"Current state before processing: {current_state}")
                
                # Add user message to state
                current_state["messages"].append(HumanMessage(content=user_message))
                current_state["waiting_for_user"] = False
                
                # Process with graph
                logger.info("Processing message with graph...")
                new_state = await graph.ainvoke(current_state)
                logger.debug(f"New state after graph processing: {new_state}")
                sessions[received_session_id] = new_state
                
                # Send complete message when streaming is done
                if new_state["messages"] and len(new_state["messages"]) > len(current_state["messages"]):
                    response_message = {
                        "type": "message", 
                        "content": new_state["messages"][-1].content,
                        "session_id": received_session_id
                    }
                    logger.info(f"Sending response message: {response_message}")
                    await websocket.send_text(json.dumps(response_message))
                
                # If we've reached a final outcome, send completion message
                if new_state["questioning_complete"]:
                    completion_message = {
                        "type": "complete", 
                        "content": {
                            "outcome": new_state["outcome"],
                            "answers": new_state["answers"]
                        },
                        "session_id": received_session_id
                    }
                    logger.info(f"Sending completion message: {completion_message}")
                    await websocket.send_text(json.dumps(completion_message))
                    # Clean up session
                    logger.info(f"Cleaning up completed session: {received_session_id}")
                    del sessions[received_session_id]
                    break
                    
            except WebSocketDisconnect:
                logger.info("Client disconnected")
                # Clean up session on disconnect
                if session_id in sessions:
                    logger.info(f"Cleaning up disconnected session: {session_id}")
                    del sessions[session_id]
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": str(e),
                    "session_id": session_id
                }))
                # Don't break the connection on error, allow retry
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": str(e),
                "session_id": session_id
            }))
        except:
            logger.error("Failed to send error message to client", exc_info=True)
        # Clean up session on error
        if session_id in sessions:
            logger.info(f"Cleaning up errored session: {session_id}")
            del sessions[session_id]

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)