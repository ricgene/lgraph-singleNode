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
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
import logging
from langsmith import trace

# Set up environment variables
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
class DeckState:
    def __init__(self):
        self.conversation_history = ""
        self.all_info_collected = False
        self.is_complete = False

llm = ChatOpenAI(model="gpt-4", temperature=0)

def assess_response(question: str, user_response: str) -> str:
    """Assess the user's response to determine what was learned."""
    assessment_prompt = f"""
You are assessing a response to a question about a Task.

Question asked: {question}
User's response: {user_response}

If the response contains useful information about the customer's Task, respond with:
"I do know [specific information learned]"

If no useful information was learned, respond with exactly:
"Thank you.  {question}"

"""
    messages = [{"role": "system", "content": assessment_prompt}]
    response = llm.invoke(messages)
    return response.content

def process_message(input_dict):
    """
    Process a message in a stateless manner, taking a single dictionary input.
    The input dictionary should contain:
    - user_input: The user's message
    - previous_state: The previous state (None for first call)
    """
    with trace("process_message", metadata={"input": input_dict}):
        # Extract input values
        user_input = input_dict.get('user_input', '')
        previous_state = input_dict.get('previous_state', None)
        
        with trace("state_initialization", metadata={"previous_state": previous_state}):
            # Initialize or use previous state
            if previous_state is None:
                state = DeckState()
            else:
                state = DeckState()
                state.conversation_history = previous_state.get('conversation_history', '')
                state.is_complete = previous_state.get('is_complete', False)
        
        # Build system prompt
        system_prompt = """You are a helpful AI Agent named Helen is helping a customer complete a home Task.  You work for Prizm which is a Real Estate Concierge Service 
        You need to collect the following information:
        1. Are they ready to discuss their Task
        2. Will they reach out to the contractor <C>
        3. Do they have any concerns or questions

        Format your responses as:
        Question: [Your next question]
        Learned: [What you've learned from the conversation so far]
        
        Start by asking about 1. above if no information has been provided yet.
        After each response, assess what new information you've learned and include it in the 'Learned' section.
        When you have all the information:
            -close the conversation with 'Thank you for selecting Prizm, have a great rest of your day!  And take the action below 'When you have all the information ...'
            -end with 'TASK_PROGRESSING' if user will move forward.  otherwise end end with 'TASK_ESCALATION'"""
        
        # Build message list
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history if it exists
        if state.conversation_history:
            messages.append({"role": "assistant", "content": state.conversation_history})
        
        # Add user input if it exists
        if user_input:
            messages.append({"role": "user", "content": user_input})
        
        with trace("llm_call", metadata={"messages": messages}):
            # Get response from LLM
            response = llm.invoke(messages)
        
        # Extract question and learned information
        response_text = response.content
        question = ""
        learned = ""
        
        # Parse the response
        if "Question:" in response_text:
            question = response_text.split("Question:")[1].split("Learned:")[0].strip()
        if "Learned:" in response_text:
            learned = response_text.split("Learned:")[1].strip()
        
        # Update conversation history with both the question and learned information
        if question:
            state.conversation_history += f"\nQuestion: {question}"
        if learned:
            state.conversation_history += f"\nLearned: {learned}"
        
        # Check if conversation is complete
        is_complete = "TASK_PROGRESSING" in response_text or "TASK_ESCALATION" in response_text
        state.is_complete = is_complete
        
        with trace("step", metadata={
            "question": question,
            "learned": learned,
            "is_complete": is_complete,
            "conversation_history": state.conversation_history
        }):
            # Return the result
            return {
                "question": question,
                "conversation_history": state.conversation_history,
                "is_complete": is_complete
            }

# Build the graph
builder = StateGraph(DeckState)
builder.add_node("collect_info", process_message)
builder.set_entry_point("collect_info")
builder.add_conditional_edges(
    "collect_info",
    lambda state: END if state.is_complete else "collect_info"
)
graph = builder.compile()

__all__ = ["graph"]

def run_example():
    """Example of how to use the process_message function"""
    print("\n=== DEBUG: Starting Conversation ===")
    
    print("----------get question 1--------")
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
    
    print("----------get question 2--------")
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
    q = 3
    while not result["is_complete"]:
        print("\n=== DEBUG: Continuing Conversation ===")
        user_input = input("You: ")
        print("User input:", user_input)
        print(f"----------get question {q}--------")
        q += 1
        
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
