# https://www.perplexity.ai/search/call-langsmith-from-gcp-SUeirpGwS..iQt1Wb6WiPw?login-new=false&login-source=visitorGate
from langgraph_sdk import get_sync_client
from dotenv import load_dotenv
import os

load_dotenv()

client = get_sync_client(
    url="https://ht-puzzled-hawk-92-1ed33bfac2835320a75061bbc8ad6652.us.langgraph.app",
    api_key=os.getenv("LANGCHAIN_API_KEY")
)

def start_conversation():
    initial_state = {
        "messages": [],
        "step": "q1",
        "iteration": 0
    }
    result = client.runs.invoke(
        None,          # Threadless run
        "superNode",   # Your workflow name
        input=initial_state
    )
    if "__interrupt__" in result:
        question = result["__interrupt__"][0].value["question"]
        print(f"QUESTION FOR USER: {question}")
        # Save result (including run_id if present) and wait for user reply
        # Present question to user via your UI/webhook/API
    else:
        print("FINAL OUTPUT:", result)

if __name__ == "__main__":
    start_conversation()
