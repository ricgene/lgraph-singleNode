from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
# from agent import create_workflow
from agent import graph
from langchain_core.messages import HumanMessage, AIMessage

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

# Create the workflow
# graph = create_workflow()

@app.get("/")
def read_root():
    return {"message": "LangGraph Agent API is running. Connect to the WebSocket at /chat"}

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Initialize state with empty message list
        initial_state = {
            "messages": [],
            "internal_memory": {},
            "current_question": 0,
            "sub_question_context": None,
            "sub_question_count": 0,
            "answers": {},
            "questioning_complete": False,
            "outcome": "needs_more_info"
        }
        
        # Function to handle streaming responses
        async def stream_handler(chunk):
            try:
                await websocket.send_text(json.dumps({"type": "chunk", "content": chunk}))
            except Exception as e:
                print(f"Error sending chunk: {e}")
        
        # Send initial message
        try:
            # Start the conversation with the initial state
            state = await graph.ainvoke(initial_state)
            
            # Send the complete initial message
            if state["messages"]:
                await websocket.send_text(json.dumps({
                    "type": "message", 
                    "content": state["messages"][-1].content
                }))
        except Exception as e:
            print(f"Error in initial state: {e}")
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
            return
        
        # Main interaction loop
        while True:
            try:
                # Receive message from user
                user_message = await websocket.receive_text()
                
                # Create a new state with the user message
                current_state = {
                    "messages": state["messages"].copy(),
                    "internal_memory": state["internal_memory"].copy(),
                    "current_question": state["current_question"],
                    "sub_question_context": state["sub_question_context"],
                    "sub_question_count": state["sub_question_count"],
                    "answers": state["answers"].copy(),
                    "questioning_complete": state["questioning_complete"],
                    "outcome": state["outcome"]
                }
                
                # Add user message to state
                current_state["messages"].append(HumanMessage(content=user_message))
                
                # Process with graph
                new_state = await graph.ainvoke(current_state)
                
                # Send complete message when streaming is done
                if new_state["messages"] and len(new_state["messages"]) > len(state["messages"]):
                    await websocket.send_text(json.dumps({
                        "type": "message", 
                        "content": new_state["messages"][-1].content
                    }))
                
                # Update state for next iteration
                state = new_state
                
                # If we've reached a final outcome, send completion message
                if state["questioning_complete"]:
                    await websocket.send_text(json.dumps({
                        "type": "complete", 
                        "content": {
                            "outcome": state["outcome"],
                            "answers": state["answers"]
                        }
                    }))
                    # End the conversation after completion
                    break
                    
            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"Error processing message: {e}")
                await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
                # Don't break the connection on error, allow retry
        
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)