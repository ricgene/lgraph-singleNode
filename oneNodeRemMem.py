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

test_api_key()

# Define the state structure
class DeckState:
    def __init__(self):
        self.conversation_history = ""
        self.all_info_collected = False
        self.is_complete = False
        logger.info(f"Initialized DeckState with attributes: {dir(self)}")

    def __str__(self):
        return f"DeckState(conversation_history={self.conversation_history}, is_complete={self.is_complete})"

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
    """
    print("\n=== DEBUG: Starting process_message ===")
    print(f"Input dictionary: {input_dict}")
    print(f"Input dictionary type: {type(input_dict)}")
    
    # Extract input values
    user_input = input_dict.get('user_input', '')
    previous_state = input_dict.get('previous_state', None)
    
    print(f"\nInitial state:")
    print(f"User input
