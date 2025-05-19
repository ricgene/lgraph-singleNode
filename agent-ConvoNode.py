from typing import TypedDict, Optional, List, Annotated, Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
from dotenv import load_dotenv
import os

# Try to load environment variables from .env file, but don't fail if it doesn't exist
try:
    load_dotenv(override=True)  # override=True means env vars take precedence over .env file
except Exception as e:
    print(f"Note: Could not load .env file: {str(e)}")
    print("Continuing with existing environment variables...")

def test_api_key():
    """Test if the OpenAI API key is loaded correctly."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ OpenAI API key is loaded successfully")
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        print(f"API Key (masked): {masked_key}")
    else:
        print("❌ OpenAI API key is not loaded")
        print("Please make sure you have either:")
        print("1. A .env file with OPENAI_API_KEY set, or")
        print("2. The OPENAI_API_KEY environment variable set directly")

test_api_key()

# Define the state structure
class DeckState(TypedDict):
    conversation_history: List[str]
    all_info_collected: bool

# Set up the LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Define the node function
def collect_deck_info(state: DeckState) -> DeckState:
    conversation = "\n".join(state.get("conversation_history", []))
    
    system_prompt = """
You are a helpful assistant helping a user plan a new back deck project.
You need to gather the following information:
1. Deck size
2. Materials
3. Budget
4. Timeline
5. Permit requirements

Check what details have been provided in the conversation so far, and ask for what is still missing.
If everything is collected, say "Thanks, I have everything I need."
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Conversation so far:\n{conversation}\n\nWhat should you say next?"}
    ]

    response = llm.invoke(messages)
    response_text = response.content

    print(f"\nAssistant: {response_text}")
    
    if "everything I need" in response_text.lower():
        return {
            "conversation_history": state["conversation_history"] + [f"Assistant: {response_text}"],
            "all_info_collected": True
        }
    else:
        user_reply = input("\nYou: ")
        return {
            "conversation_history": state["conversation_history"] + [f"Assistant: {response_text}", f"You: {user_reply}"],
            "all_info_collected": False
        }

# Build the graph
builder = StateGraph(DeckState)
builder.add_node("collect_info", collect_deck_info)
builder.set_entry_point("collect_info")
builder.add_conditional_edges(
    "collect_info",
    lambda state: END if state["all_info_collected"] else "collect_info"
)
graph = builder.compile()

__all__ = ["graph"]


if __name__ == "__main__":
    # Run the graph
    initial_state = {"conversation_history": [], "all_info_collected": False}
    final_state = graph.invoke(initial_state)

    # Print final result
    print("\nFinal transcript:")
    for line in final_state["conversation_history"]:
        print(line)
