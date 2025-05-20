### to run latest "superNode": "agent-ConvoNode:workflow"

from langgraph_sdk import get_sync_client
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("LANGCHAIN_API_KEY"):
    raise ValueError("LANGCHAIN_API_KEY not found in environment variables. Please add it to your .env file.")

# Use the correct API key
client = get_sync_client(
    url="https://ht-puzzled-hawk-92-1ed33bfac2835320a75061bbc8ad6652.us.langgraph.app", 
    api_key="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"
)

# Stream the response with the correct graph name
for chunk in client.runs.stream(
    None,  # None means threadless run
    "superNode",  # Use the correct graph name from the error message
    input={ "messages": [], "step": "q1"},
    stream_mode="updates"
):
    print(chunk.data)