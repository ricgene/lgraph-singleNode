from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
# from agent import create_workflow
from agent import graph

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
        # Initialize state
        state = {
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
            await websocket.send_text(json.dumps({"type": "chunk", "content": chunk}))
        
        # Send initial message
        initial_state = await graph.ainvoke(
            state, 
            {"stream_handler": stream_handler}
        )
        state = initial_state
        
        # Send the complete initial message
        await websocket.send_text(json.dumps({
            "type": "message", 
            "content": state["messages"][-1].content
        }))
        
        # Main interaction loop
        while True:
            # Receive message from user
            user_message = await websocket.receive_text()
            
            try:
                # Process with graph - using async invocation for streaming
                new_state = await graph.ainvoke(
                    state, 
                    {"user_input": user_message, "stream_handler": stream_handler}
                )
                
                # Send complete message when streaming is done
                if len(new_state["messages"]) > len(state["messages"]):
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
                    
            except Exception as e:
                # Send error message
                await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
                print(f"Error processing message: {e}")
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)