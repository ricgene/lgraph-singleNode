#!/usr/bin/env python3
"""
Quick test to verify LangGraph SDK usage
"""

import os

LANGGRAPH_DEPLOYMENT_URL = "https://prizm2-9d0348d2abe5594d8b533da6f9b05cac.us.langgraph.app"
LANGGRAPH_API_KEY = "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"

def test_langgraph_sdk():
    try:
        from langgraph_sdk import get_sync_client
        
        client = get_sync_client(url=LANGGRAPH_DEPLOYMENT_URL, api_key=LANGGRAPH_API_KEY)
        print("✅ Client created successfully")
        
        # Create thread
        thread = client.threads.create()
        print(f"✅ Thread created: {type(thread)} - {thread}")
        
        # Test input
        test_input = {
            "user_input": "Hello, this is a test",
            "user_email": "test@example.com",
        }
        
        # Create run
        run = client.runs.create(
            thread_id=thread["thread_id"],
            assistant_id="moBettah",
            input=test_input
        )
        print(f"✅ Run created: {type(run)} - {run}")
        
        # Wait for completion
        result = client.runs.wait(
            thread_id=thread["thread_id"],
            run_id=run["run_id"]
        )
        print(f"✅ Result: {type(result)} - {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_langgraph_sdk()