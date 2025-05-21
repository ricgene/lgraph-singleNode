from typing import TypedDict, List, Dict, Optional
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from dotenv import load_dotenv
import os
import json

try:
    load_dotenv(override=True)
except Exception as e:
    print(f"Note: Could not load .env file: {str(e)}")

def test_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ OpenAI API key is loaded successfully")
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        print(f"API Key (masked): {masked_key}")
    else:
        print("❌ OpenAI API key is not loaded")
        print("Please set OPENAI_API_KEY in your .env or environment.")

test_api_key()

class DeckState(TypedDict, total=False):
    conversation_history: str  # String containing the Q&A history
    all_info_collected: bool
    last_assistant_message: str

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

def collect_deck_info(state: DeckState) -> DeckState:
    print("\n=== DEBUG: collect_deck_info input ===")
    print("State:", state)
    
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
    if state.get("user_response"):
        messages.append({"role": "user", "content": state["user_response"]})

    # ---- DEBUG PRINT ----
    print("\n=== DEBUG: State at Start of Turn ===")
    print("Conversation History:")
    print(state.get("conversation_history", "None"))
    print("\nUser Response:")
    print(state.get("user_response", "None"))
    print("\nMessages being sent to LLM:")
    print(json.dumps(messages, indent=2))
    print("=== END DEBUG ===\n")
    # ---------------------

    response = llm.invoke(messages)
    response_text = response.content

    # If we have a user response, assess what was learned
    if state.get("user_response"):
        assessment = assess_response(response_text, state["user_response"])
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
            "conversation_history": new_history,
            "all_info_collected": True
        }
    else:
        return interrupt({
            "question": response_text,
            "conversation_history": new_history,
            "last_assistant_message": response_text
        })

builder = StateGraph(DeckState)
builder.add_node("collect_info", collect_deck_info)
builder.set_entry_point("collect_info")
builder.add_conditional_edges(
    "collect_info",
    lambda state: END if state.get("all_info_collected") else "collect_info"
)
graph = builder.compile()

__all__ = ["graph"]

def process_message(user_input: str, previous_state: Optional[Dict] = None) -> Dict:
    """
    Process a single message and return the updated state.
    This is the main function to be called from the server.
    
    Args:
        user_input: The user's message
        previous_state: The previous state containing conversation history
    
    Returns:
        Dict containing:
        - question: The assistant's response (if conversation continues)
        - conversation_history: The Q&A history
        - is_complete: Whether the conversation is complete
    """
    # Initialize or use previous state
    state = previous_state or {
        "conversation_history": "",
        "all_info_collected": False
    }
    
    # Add user input to state
    state["user_response"] = user_input
    
    # Process the message
    result = graph.invoke(state)
    
    # Check if conversation is complete
    if not result.get("__interrupt__"):
        return {
            "question": "Conversation complete!",
            "conversation_history": result["conversation_history"],
            "is_complete": True
        }
    
    # Get the interrupt payload
    interrupt_payload = result["__interrupt__"][0].value
    
    # Return the updated state
    return {
        "question": interrupt_payload["question"],
        "conversation_history": interrupt_payload["conversation_history"],
        "is_complete": False
    }

def run_example():
    """Example of how to use the process_message function"""
    # Start with empty state to get first question
    estate = None
    result = process_message("", estate)  # Empty string to get first question
    print("\nAssistant:", result["question"])
    
    while True:
        user_input = input("You: ")
        # Pass the previous state with conversation history
        estate = {
            "conversation_history": result["conversation_history"],
            "all_info_collected": False
        }
        result = process_message(user_input, estate)
        
        print("\nAssistant:", result["question"])
        
        if result["is_complete"]:
            print("\nConversation complete!")
            print("\nFull Conversation History:")
            print(result["conversation_history"])
            break

if __name__ == "__main__":
    run_example()
