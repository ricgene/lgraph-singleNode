from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from agent import graph
from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any
import uuid

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
    return {
        "messages": [],
        "internal_memory": {},
        "current_question": 0,
        "sub_question_context": None,
        "sub_question_count": 0,
        "answers": {},
        "questioning_complete": False,
        "outcome": "needs_more_info",
        "waiting_for_user": False
    }

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
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    try:
        # Initialize new session
        sessions[session_id] = create_initial_state()
        
        # Function to handle streaming responses
        async def stream_handler(chunk):
            try:
                await websocket.send_text(json.dumps({
                    "type": "chunk", 
                    "content": chunk,
                    "session_id": session_id
                }))
            except Exception as e:
                print(f"Error sending chunk: {e}")
        
        # Send initial message immediately
        try:
            # Start the conversation with the initial state
            state = await graph.ainvoke(sessions[session_id])
            sessions[session_id] = state  # Update session state
            
            # Send the complete initial message
            if state["messages"]:
                await websocket.send_text(json.dumps({
                    "type": "message", 
                    "content": state["messages"][-1].content,
                    "session_id": session_id
                }))
        except Exception as e:
            print(f"Error in initial state: {e}")
            await websocket.send_text(json.dumps({
                "type": "error", 
                "content": str(e),
                "session_id": session_id
            }))
            return
        
        # Main interaction loop
        while True:
            try:
                # Receive message from user
                data = await websocket.receive_text()
                message_data = json.loads(data)
                user_message = message_data.get("content", "")
                received_session_id = message_data.get("session_id")
                
                # If no session ID provided, create a new session
                if not received_session_id:
                    received_session_id = str(uuid.uuid4())
                    sessions[received_session_id] = create_initial_state()
                
                # Validate session
                if received_session_id not in sessions:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": "Invalid session ID"
                    }))
                    continue
                
                # Get current state
                current_state = sessions[received_session_id]
                
                # Add user message to state
                current_state["messages"].append(HumanMessage(content=user_message))
                current_state["waiting_for_user"] = False
                
                # Process with graph
                new_state = await graph.ainvoke(current_state)
                sessions[received_session_id] = new_state  # Update session state
                
                # Send complete message when streaming is done
                if new_state["messages"] and len(new_state["messages"]) > len(current_state["messages"]):
                    await websocket.send_text(json.dumps({
                        "type": "message", 
                        "content": new_state["messages"][-1].content,
                        "session_id": received_session_id
                    }))
                
                # If we've reached a final outcome, send completion message
                if new_state["questioning_complete"]:
                    await websocket.send_text(json.dumps({
                        "type": "complete", 
                        "content": {
                            "outcome": new_state["outcome"],
                            "answers": new_state["answers"]
                        },
                        "session_id": received_session_id
                    }))
                    # Clean up session
                    del sessions[received_session_id]
                    break
                    
            except WebSocketDisconnect:
                print("Client disconnected")
                # Clean up session on disconnect
                if session_id in sessions:
                    del sessions[session_id]
                break
            except Exception as e:
                print(f"Error processing message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": str(e),
                    "session_id": session_id
                }))
                # Don't break the connection on error, allow retry
        
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": str(e),
                "session_id": session_id
            }))
        except:
            pass
        # Clean up session on error
        if session_id in sessions:
            del sessions[session_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)