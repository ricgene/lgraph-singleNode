from typing import TypedDict, List, Dict, Optional
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
from dotenv import load_dotenv
import os
import json

# Try to load environment variables from .env file, but don't fail if it doesn't exist
try:
    load_dotenv(override=True)
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
        print("Please set OPENAI_API_KEY in your .env or environment.")

test_api_key()

# Define the state structure
class DeckState(TypedDict, total=False):
    conversation_history: str  # String containing the Q&A history
    all_info_collected: bool

llm = ChatOpenAI(model="gpt-4", temperature=0)

def assess_response(question: str, user_response: str) -> str:
    """Assess the user's response to determine what was learned."""
    assessment_prompt = f"""
You are assessing a response to a question about a deck building project.

Question asked: {question}
User's response: {user_response}

If the response contains useful information about the deck project, respond with:
"I do know [specific information learned]"

If no useful information was learned, respond with exactly:
"..."

"""
    messages = [{"role": "system", "content": assessment_prompt}]
    response = llm.invoke(messages)
    return response.content

def process_message(input_dict: Dict) -> Dict:
    """
    Process a single message and return the updated state.
    This is the main function to be called from the cloud.
    
    Args:
        input_dict: Dictionary containing:
            - user_input: The user's message
            - previous_state: The previous state containing conversation history
    
    Returns:
        Dict containing:
        - question: The assistant's response (if conversation continues)
        - conversation_history: The Q&A history
        - is_complete: Whether the conversation is complete
    """
    user_input = input_dict.get("user_input", "")
    previous_state = input_dict.get("previous_state")
    
    print("\n=== DEBUG: Input Received ===")
    print("Input dictionary:", json.dumps(input_dict, indent=2))
    
    # Initialize or use previous state
    state = previous_state or {
        "conversation_history": "",
        "all_info_collected": False
    }
    
    # Build the system prompt
    system_prompt = """
You are a helpful assistant helping a user plan a new back deck project.
You need to gather the following information:
1. Deck size
2. Materials
3. Budget
4. Timeline
5. Permit requirements

IMPORTANT: If this is the first message (empty string), respond with exactly:
"I'd like to discuss the deck you are building, my first question is what are the dimensions?"

If you have all the information needed, respond with:
"---begin-deck-building---
[summary of all information gathered]"

"""
    # Add conversation history if it exists
    if state.get("conversation_history"):
        system_prompt += "\nPrevious customer interactions:\n" + state["conversation_history"]
    
    # Build the messages list
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add the last user response if it exists
    if user_input:
        messages.append({"role": "user", "content": user_input})

    # ---- DEBUG PRINT ----
    print("\n=== DEBUG: State at Start of Turn ===")
    print("Conversation History:")
    print(state.get("conversation_history", "None"))
    print("\nUser Response:")
    print(user_input if user_input else "None")
    print("\nMessages being sent to LLM:")
    print(json.dumps(messages, indent=2))
    print("=== END DEBUG ===\n")
    # ---------------------

    response = llm.invoke(messages)
    response_text = response.content

    # If we have a user response, assess what was learned
    if user_input:
        assessment = assess_response(response_text, user_input)
        print("\n=== DEBUG: Response Assessment ===")
        print("Assessment:", assessment)
        
        # Only update history if we learned something new
        if "I do know" in assessment:
            new_history = state.get("conversation_history", "") + assessment + "\n"
        else:
            new_history = state.get("conversation_history", "")
    else:
        new_history = state.get("conversation_history", "")

    print("\n=== DEBUG: New history created ===")
    print("New history:", new_history)

    # Check if the response indicates all information is collected
    if "---begin-deck-building---" in response_text:
        return {
            "question": response_text,
            "conversation_history": new_history,
            "is_complete": True
        }
    else:
        return {
            "question": response_text,
            "conversation_history": new_history,
            "is_complete": False
        }

# Build the graph
builder = StateGraph(DeckState)
builder.add_node("collect_info", process_message)
builder.set_entry_point("collect_info")
builder.add_conditional_edges(
    "collect_info",
    lambda state: END if state.get("is_complete") else "collect_info"
)
graph = builder.compile()

__all__ = ["graph"]

def run_example():
    """Example of how to use the process_message function"""
    print("\n=== DEBUG: Starting Conversation ===")
    
    # First call - get initial question
    first_input = {
        "user_input": "",
        "previous_state": None
    }
    print("First call input:", json.dumps(first_input, indent=2))
    result = process_message(first_input)
    print("First call result:", json.dumps(result, indent=2))
    print("\nAssistant:", result["question"])
    
    # Get user's first response
    print("\n=== DEBUG: Getting First User Response ===")
    user_input = input("You: ")
    print("User input:", user_input)
    
    # Second call - process first response
    second_input = {
        "user_input": user_input,
        "previous_state": {
            "conversation_history": result["conversation_history"],
            "all_info_collected": False
        }
    }
    print("\n=== DEBUG: Processing First Response ===")
    print("Second call input:", json.dumps(second_input, indent=2))
    result = process_message(second_input)
    print("Second call result:", json.dumps(result, indent=2))
    print("\nAssistant:", result["question"])
    
    # Continue conversation until complete
    while not result["is_complete"]:
        print("\n=== DEBUG: Continuing Conversation ===")
        user_input = input("You: ")
        print("User input:", user_input)
        
        next_input = {
            "user_input": user_input,
            "previous_state": {
                "conversation_history": result["conversation_history"],
                "all_info_collected": False
            }
        }
        print("Next call input:", json.dumps(next_input, indent=2))
        result = process_message(next_input)
        print("Call result:", json.dumps(result, indent=2))
        print("\nAssistant:", result["question"])
    
    # Print final conversation history
    print("\n=== DEBUG: Conversation Complete ===")
    print("Final state:", json.dumps(result, indent=2))
    print("\nConversation complete!")
    print("\nFull Conversation History:")
    print(result["conversation_history"])

if __name__ == "__main__":
    run_example()
