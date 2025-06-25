#!/usr/bin/env python3
"""
Test script to verify the deployed moBettah service can be called via langgraph_sdk.
This simulates what your cloud function will do.
"""

import os
import json
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

# Load environment variables
load_dotenv()

def test_deployed_langgraph():
    """Test calling the deployed moBettah service."""
    
    # Get LangGraph deployment URL and API key from environment
    langgraph_deployment_url = os.getenv("LANGGRAPH_DEPLOYMENT_URL")
    langgraph_api_key = os.getenv("LANGGRAPH_API_KEY")
    
    if not langgraph_deployment_url:
        print("❌ LANGGRAPH_DEPLOYMENT_URL not found in environment variables")
        print("Please set LANGGRAPH_DEPLOYMENT_URL in your .env file")
        return
    
    if not langgraph_api_key:
        print("❌ LANGGRAPH_API_KEY not found in environment variables")
        print("Please set LANGGRAPH_API_KEY in your .env file")
        return
    
    print(f"📡 Testing deployed LangGraph service: {langgraph_deployment_url}")
    print(f"🔑 API Key (masked): {langgraph_api_key[:4]}...{langgraph_api_key[-4:]}")
    
    try:
        # Initialize the langgraph client
        client = get_sync_client(
            url=langgraph_deployment_url,
            api_key=langgraph_api_key
        )
        
        # Test input data matching oneNodeRemMem expected format
        test_input = {
            "user_input": "Yes, I'm ready to discuss my task",
            "previous_state": {
                "conversation_history": "",
                "is_complete": False,
                "user_email": "test@example.com"
            }
        }
        
        print(f"\n📤 Sending test input:")
        print(json.dumps(test_input, indent=2))
        
        # Stream the graph execution
        print(f"\n🔄 Streaming response from 'moBettah':")
        graph_output = []
        non_null_chunks = []
        for chunk in client.runs.stream(
            None,  # Threadless run
            "moBettah",  # Name of your deployed assistant
            input=test_input,
            stream_mode="updates",
        ):
            print(f"📥 Event type: {chunk.event}")
            print(f"📥 Chunk data: {json.dumps(chunk.data, indent=2)}")
            graph_output.append(chunk.data)
            # Check for non-null or meaningful data
            if chunk.data and (not isinstance(chunk.data, dict) or any(v is not None for v in chunk.data.values())):
                non_null_chunks.append(chunk.data)
        
        print(f"\n✅ Successfully received {len(graph_output)} chunks from LangGraph\n")
        # Summarize the results
        if not non_null_chunks:
            print("⚠️ All returned data was null. No meaningful output from the graph.")
        else:
            print(f"🎯 Non-null/meaningful chunks received:")
            for i, chunk in enumerate(non_null_chunks, 1):
                print(f"--- Chunk {i} ---")
                print(json.dumps(chunk, indent=2))
                # Highlight if it contains question/conversation_history
                if isinstance(chunk, dict) and ("question" in chunk or "conversation_history" in chunk):
                    print("   ⬆️ This chunk contains a question or conversation history!")
        print("\nTest complete.")
    except Exception as error:
        print(f"❌ Error testing deployed LangGraph: {error}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_deployed_langgraph() 