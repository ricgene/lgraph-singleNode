
# https://www.perplexity.ai/search/call-langsmith-from-gcp-SUeirpGwS..iQt1Wb6WiPw?login-new=false&login-source=visitorGate

from langgraph_sdk import get_sync_client
from dotenv import load_dotenv
import os
import json

load_dotenv()

def langgraph_agent(request):
    """HTTP Cloud Function to handle LangGraph agent interactions"""
    client = get_sync_client(
        url=os.getenv("LANGGRAPH_DEPLOYMENT_URL"),
        api_key=os.getenv("LANGSMITH_API_KEY")
    )
    
    # Parse request data
    request_data = request.get_json()
    is_new_conversation = request_data.get("new_conversation", True)
    user_input = request_data.get("user_input", "")
    previous_state = request_data.get("state", {})

    try:
        if is_new_conversation:
            # Start new conversation
            result = client.runs.invoke(
                None,
                "superNode",  # Your workflow name
                input={
                    "messages": [],
                    "step": "q1",
                    "iteration": 0
                }
            )
        else:
            # Resume existing conversation
            result = client.runs.invoke(
                None,
                "superNode",
                input={
                    **previous_state,
                    "__resume__": user_input
                }
            )

        if "__interrupt__" in result:
            return {
                "question": result["__interrupt__"][0].value["question"],
                "state": {k: v for k, v in result.items() if k != "__interrupt__"},
                "completed": False
            }, 200
        else:
            return {
                "response": result.get("messages", [])[-1].content if result.get("messages") else "Done",
                "completed": True
            }, 200

    except Exception as e:
        return {"error": str(e)}, 500
