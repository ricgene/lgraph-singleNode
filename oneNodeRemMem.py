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
import sys
from langgraph.prebuilt import ToolNode
import logging
from langchain_core.tracers import ConsoleCallbackHandler
from langchain_core.tracers.langchain import LangChainTracer
import requests
# from langchain_core.callbacks import get_callback_manager  # <-- removed

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log environment information
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables: {dict(os.environ)}")

# Try to load environment variables from .env file, but don't fail if it doesn't exist
try:
    load_dotenv(override=True)
    logger.info("Successfully loaded .env file")
except Exception as e:
    logger.warning(f"Could not load .env file: {str(e)}")
    logger.info("Continuing with existing environment variables...")

# Set up environment variables for LangChain tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")  # Get from .env file
os.environ["LANGCHAIN_PROJECT"] = "lgraph-singleNode"  # Your project name
os.environ["LANGCHAIN_TRACING_ENABLED"] = "true"

def test_api_key():
    """Test if the OpenAI API key is loaded correctly."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.info("✅ OpenAI API key is loaded successfully")
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        logger.info(f"API Key (masked): {masked_key}")
    else:
        logger.error("❌ OpenAI API key is not loaded")
        logger.error("Please set OPENAI_API_KEY in your .env or environment.")

def send_email(recipient_email: str, subject: str, body: str) -> bool:
    """
    Send an email by calling the deployed GCP email function.
    
    Args:
        recipient_email: Email address to send to
        subject: Email subject
        body: Email body text
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get the deployed email function URL from environment
        email_function_url = os.getenv("EMAIL_FUNCTION_URL")
        
        if not email_function_url:
            logger.error("❌ EMAIL_FUNCTION_URL not found in environment variables")
            logger.error("Please set EMAIL_FUNCTION_URL in your .env file")
            return False
        
        # Prepare the payload for the email function
        payload = {
            "to": recipient_email,
            "subject": subject,
            "body": body
        }
        
        # Call the deployed email function
        response = requests.post(email_function_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Email sent successfully to {recipient_email}")
            return True
        else:
            logger.error(f"❌ Email function returned status {response.status_code}: {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error sending email: {str(e)}")
        return False

test_api_key()

# Define the state structure
class DeckState:
    def __init__(self):
        self.conversation_history = ""
        self.all_info_collected = False
        self.is_complete = False
        self.turn_count = 0
        self.user_email = ""  # Add email field to state
        logger.info(f"Initialized DeckState with attributes: {dir(self)}")

    def __str__(self):
        return f"DeckState(conversation_history={self.conversation_history}, is_complete={self.is_complete}, turn_count={self.turn_count}, user_email={self.user_email})"

    def __repr__(self):
        return self.__str__()

llm = ChatOpenAI(model="gpt-4", temperature=0)

# Set up tracing and console handler for use in config
tracer = LangChainTracer()
console_handler = ConsoleCallbackHandler()
CALLBACKS = [tracer, console_handler]

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
    response = llm.invoke(messages, config={"callbacks": CALLBACKS})
    return response.content

def process_message(input_dict):
    """
    Process a message in a stateless manner, taking a single dictionary input.
    The input dictionary should contain:
    - user_input: The user's message
    - previous_state: The previous state (None for first call)
    - user_email: The user's email address (optional, can be set in first call)
    """
    print("\n=== DEBUG: Starting process_message ===")
    print(f"Input dictionary: {input_dict}")
    print(f"Input dictionary type: {type(input_dict)}")
    
    # Extract input values, handling both dict and DeckState cases
    if isinstance(input_dict, dict):
        user_input = input_dict.get('user_input', '')
        previous_state = input_dict.get('previous_state', None)
        user_email = input_dict.get('user_email', '')
    else:
        # If input_dict is a DeckState object
        user_input = getattr(input_dict, 'user_input', '')
        previous_state = getattr(input_dict, 'previous_state', None)
        user_email = getattr(input_dict, 'user_email', '')
    
    print(f"\nInitial state:")
    print(f"User input: {user_input}")
    print(f"User email: {user_email}")
    print(f"Previous state: {previous_state}")
    print(f"Previous state type: {type(previous_state)}")
    
    # Initialize or use previous state
    if previous_state is None:
        state = DeckState()
        state.user_email = user_email  # Set email from input
        print("\nCreated new state")
        print(f"New state attributes: {dir(state)}")
    else:
        state = DeckState()
        if isinstance(previous_state, dict):
            state.conversation_history = previous_state.get('conversation_history', '')
            state.is_complete = previous_state.get('is_complete', False)
            state.user_email = previous_state.get('user_email', user_email)
        else:
            state.conversation_history = getattr(previous_state, 'conversation_history', '')
            state.is_complete = getattr(previous_state, 'is_complete', False)
            state.user_email = getattr(previous_state, 'user_email', user_email)
        print(f"\nRestored state with conversation history: {state.conversation_history}")
        print(f"Restored state attributes: {dir(state)}")
        print(f"Restored state is_complete: {state.is_complete}")
        print(f"Restored state user_email: {state.user_email}")
    
    # Count turns by counting Q&A pairs in conversation history
    turn_count = state.conversation_history.count("Question:")
    print(f"\nCurrent turn count (from Q&A pairs): {turn_count}")
    
    # Check if we've reached the maximum number of turns
    if turn_count >= 7:
        state.is_complete = True
        final_message = "Thank you for your time. We've reached the maximum number of turns for this conversation."
        
        # Send final email if we have user's email
        if state.user_email:
            send_email(
                state.user_email,
                "Prizm Task Conversation Complete",
                final_message
            )
        
        return {
            "question": final_message,
            "conversation_history": state.conversation_history,
            "is_complete": True,
            "completion_state": "OTHER",
            "user_email": state.user_email
        }
    
    # Build system prompt
    system_prompt = f"""You are a helpful AI Agent named Helen is helping a customer complete a home Task.  You work for Prizm which is a Real Estate Concierge Service 
    You need to collect the following information:
    1. Are they ready to discuss their Task
    2. Will they reach out to the contractor <C>
    3. Do they have any concerns or questions

    Format your responses as:
    Question: [Your next question]
    Learned: [What you've learned from the conversation so far]
    
    IMPORTANT RULES:
    1. ALWAYS format your response with "Question:" and "Learned:" sections
    2. If the user's response is unclear or doesn't answer your question:
       - Rephrase your question to be more specific
       - In the "Learned" section, note that the response was unclear
    3. Start by asking about 1. above if no information has been provided yet
    4. After each response, assess what new information you've learned and include it in the 'Learned' section
    5. When you have all the information:
        -close the conversation with 'Thank you for selecting Prizm, have a great rest of your day!  And take the action below 'When you have all the information ...'
        -end with 'TASK_PROGRESSING' if user will move forward.  otherwise end end with 'TASK_ESCALATION'
    6. Current turn count: {turn_count}/7. You have {7 - turn_count} turns remaining."""
    
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
    
    print("\nMessages being sent to LLM:")
    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    
    # Get response from LLM, with tracing and console callbacks
    response = llm.invoke(messages, config={"callbacks": CALLBACKS})
    print(f"\nLLM Response: {response}")
    
    # Extract question and learned information
    response_text = response.content
    question = ""
    learned = ""
    
    # Parse the response
    if "Question:" in response_text:
        question = response_text.split("Question:")[1].split("Learned:")[0].strip()
    if "Learned:" in response_text:
        learned = response_text.split("Learned:")[1].strip()
    
    # If the response wasn't properly formatted, use the entire response as the question
    if not question and not learned:
        question = response_text.strip()
        learned = "No clear information provided in the response."
    
    # Update conversation history with both the question and learned information
    if question:
        state.conversation_history += f"\nQuestion: {question}"
    if learned:
        state.conversation_history += f"\nLearned: {learned}"
    
    # Check if conversation is complete
    is_complete = "TASK_PROGRESSING" in response_text or "TASK_ESCALATION" in response_text
    
    # Also check if the conversation history already contains completion markers
    if not is_complete and state.conversation_history:
        is_complete = "TASK_PROGRESSING" in state.conversation_history or "TASK_ESCALATION" in state.conversation_history
    
    state.is_complete = is_complete
    
    # Determine completion state
    completion_state = "OTHER"
    if "TASK_PROGRESSING" in response_text or "TASK_PROGRESSING" in state.conversation_history:
        completion_state = "TASK_PROGRESSING"
    elif "TASK_ESCALATION" in response_text or "TASK_ESCALATION" in state.conversation_history:
        completion_state = "TASK_ESCALATION"
    
    # If conversation is complete, don't send another question
    if is_complete:
        question = ""
        # Send completion message if we haven't already
        if state.user_email and "Thank you for selecting Prizm" not in state.conversation_history:
            send_email(
                state.user_email,
                "Prizm Task Conversation Complete",
                "Thank you for your time. We've completed our conversation about your task."
            )
    # Send email with the question if we have user's email and this is not the final message
    elif state.user_email and question and not is_complete:
        email_body = f"""Hello!

Helen from Prizm here. I have a question for you about your task:

{question}

Please reply to this email with your response.

Best regards,
Helen
Prizm Real Estate Concierge Service"""
        
        send_email(
            state.user_email,
            f"Prizm Task Question #{turn_count + 1}",
            email_body
        )
    
    print("\nFinal state:")
    print(f"Question: {question}")
    print(f"Learned: {learned}")
    print(f"Conversation history: {state.conversation_history}")
    print(f"Is complete: {is_complete}")
    print(f"Completion state: {completion_state}")
    print(f"State type: {type(state)}")
    print(f"State attributes: {dir(state)}")
    
    # Return the result
    return {
        "question": question,
        "conversation_history": state.conversation_history,
        "is_complete": is_complete,
        "completion_state": completion_state,
        "user_email": state.user_email
    }

# Build the graph
builder = StateGraph(DeckState)
builder.add_node("collect_info", process_message)
builder.set_entry_point("collect_info")
builder.add_conditional_edges(
    "collect_info",
    lambda state: END if (hasattr(state, 'is_complete') and state.is_complete) or (isinstance(state, dict) and state.get('is_complete', False)) else "collect_info"
)
graph = builder.compile()

# Export the graph for LangGraph
__all__ = ["graph"]

def run_example():
    """Example of how to use the process_message function"""
    print("\n=== DEBUG: Starting Conversation ===")
    
    # Get user's email address
    user_email = input("Please enter your email address: ").strip()
    if not user_email:
        print("No email provided. Email functionality will be disabled.")
        user_email = ""
    
    print("----------get question 1--------")
    first_input = {
        "user_input": "",
        "previous_state": None,
        "user_email": user_email
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
            "all_info_collected": False,
            "user_email": result["user_email"]
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
                "all_info_collected": False,
                "user_email": result["user_email"]
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
