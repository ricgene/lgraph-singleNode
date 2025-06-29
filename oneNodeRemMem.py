"""
This is a simple example of a LangGraph state graph that collects information from a user.

{
  "conversation_history": "Question: Hello...\nLearned: ...",
  "is_complete": false,
  "turn_count": 3,
  "user_email": "user@example.com",
  "completion_state": "in_progress"
}

"""
import os
import sys
import json
import logging
import asyncio
from typing import Dict, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langchain_core.tracers import ConsoleCallbackHandler
from langchain_core.tracers.langchain import LangChainTracer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    load_dotenv(override=True)
    logger.info("Successfully loaded .env file")
except Exception as e:
    logger.warning(f"Could not load .env file: {str(e)}")

# Set up environment variables for LangChain tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = "lgraph-singleNode"
os.environ["LANGCHAIN_TRACING_ENABLED"] = "true"

# Configuration
AGENT_PROMPT_TYPE = os.getenv("AGENT_PROMPT_TYPE", "prizm")  # prizm, generic, debug

# System prompts configuration
SYSTEM_PROMPTS = {
    "prizm": """You are a helpful AI Agent named Helen helping a customer complete a home Task for Prizm Real Estate Concierge Service.
You need to collect the following information:
1. Are they ready to discuss their Task
2. Will they reach out to the contractor <C>
3. Do they have any concerns or questions...
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
    - close the conversation with 'Thank you for selecting Prizm, have a great rest of your day!  And take the action below 'When you have all the information ...'
    - end with 'TASK_PROGRESSING' if user will move forward.  otherwise end with 'TASK_ESCALATION'
6. Current turn count: {turn_count}/7. You have {remaining_turns} turns remaining.""",

    "generic": """You are a helpful AI assistant. Your goal is to understand what the user needs and provide helpful responses.
Format your responses as:
Question: [Your next question or response]
Learned: [What you've learned from this interaction]

RULES:
1. Always use the Question/Learned format
2. Ask follow-up questions to better understand the user's needs
3. When you have enough information to help, end with 'TASK_COMPLETE'
4. Current turn count: {turn_count}/7. You have {remaining_turns} turns remaining.""",

    "debug": """DEBUG MODE: Simple test agent for development.
Format responses as:
Question: [Simple question or acknowledgment]
Learned: [Echo what user said]

RULES:
1. Keep responses short and simple
2. Always use Question/Learned format
3. End with 'TASK_PROGRESSING' after 3 turns for testing
4. Current turn count: {turn_count}/7. You have {remaining_turns} turns remaining."""
}

def test_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.info("✅ OpenAI API key loaded")
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        logger.info(f"API Key (masked): {masked_key}")
    else:
        logger.error("❌ OPENAI_API_KEY missing")

def get_system_prompt(turn_count: int) -> str:
    """Get the system prompt based on configuration."""
    prompt_type = AGENT_PROMPT_TYPE.lower()
    if prompt_type not in SYSTEM_PROMPTS:
        logger.warning(f"Unknown prompt type '{prompt_type}', defaulting to 'prizm'")
        prompt_type = "prizm"
    
    logger.info(f"Using prompt type: {prompt_type}")
    remaining_turns = 7 - turn_count
    return SYSTEM_PROMPTS[prompt_type].format(turn_count=turn_count, remaining_turns=remaining_turns)

test_api_key()

llm = ChatOpenAI(model="gpt-4", temperature=0)
tracer = LangChainTracer()
console_handler = ConsoleCallbackHandler()
CALLBACKS = [tracer, console_handler]

async def process_message(input_dict: Dict) -> Dict:
    """
    Process a message using dict-based state management.
    """
    # Extract input values
    user_input = input_dict.get('user_input', '')
    previous_state = input_dict.get('previous_state', None)
    user_email = input_dict.get('user_email', '')

    # Initialize or restore state using dicts
    if previous_state is None:
        state = {
            'conversation_history': '',
            'is_complete': False,
            'turn_count': 0,
            'user_email': user_email
        }
    else:
        state = {
            'conversation_history': previous_state.get('conversation_history', ''),
            'is_complete': previous_state.get('is_complete', False),
            'turn_count': previous_state.get('turn_count', 0),
            'user_email': previous_state.get('user_email', user_email)
        }

    # Increment turn count for this interaction
    state['turn_count'] += 1
    turn_count = state['turn_count']

    # Check for max turns
    if turn_count >= 7:
        state['is_complete'] = True
        final_message = "Thank you for your time. We've reached the maximum number of turns for this conversation."
        return {
            "question": final_message,
            "conversation_history": state['conversation_history'],
            "is_complete": True,
            "completion_state": "OTHER",
            "user_email": state['user_email'],
            "turn_count": turn_count
        }

    # Build system prompt using configuration
    system_prompt = get_system_prompt(turn_count)

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    if state['conversation_history']:
        messages.append({"role": "assistant", "content": state['conversation_history']})
    if user_input:
        messages.append({"role": "user", "content": user_input})

    # Use async LLM call if available, otherwise wrap in executor
    if hasattr(llm, "ainvoke"):
        response = await llm.ainvoke(messages, config={"callbacks": CALLBACKS})
    else:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: llm.invoke(messages, config={"callbacks": CALLBACKS}))

    response_text = response.content
    question = ""
    learned = ""
    if "Question:" in response_text:
        question = response_text.split("Question:")[1].split("Learned:")[0].strip()
    if "Learned:" in response_text:
        learned = response_text.split("Learned:")[1].strip()
    if not question and not learned:
        question = response_text.strip()
        learned = "No clear information provided in the response."

    # Update conversation history
    if question:
        state['conversation_history'] += f"\nQuestion: {question}"
    if learned:
        state['conversation_history'] += f"\nLearned: {learned}"

    # Check for completion
    is_complete = "TASK_PROGRESSING" in response_text or "TASK_ESCALATION" in response_text
    if not is_complete and state['conversation_history']:
        is_complete = "TASK_PROGRESSING" in state['conversation_history'] or "TASK_ESCALATION" in state['conversation_history']
    state['is_complete'] = is_complete

    # Determine completion state
    completion_state = "OTHER"
    if "TASK_PROGRESSING" in response_text or "TASK_PROGRESSING" in state['conversation_history']:
        completion_state = "TASK_PROGRESSING"
    elif "TASK_ESCALATION" in response_text or "TASK_ESCALATION" in state['conversation_history']:
        completion_state = "TASK_ESCALATION"

    # Clear question if complete (no more questions needed)
    if is_complete:
        question = ""

    return {
        "question": question,
        "conversation_history": state['conversation_history'],
        "is_complete": is_complete,
        "completion_state": completion_state,
        "user_email": state['user_email'],
        "turn_count": turn_count
    }

# Build the graph using dict-based state
builder = StateGraph(dict)
builder.add_node("collect_info", process_message)
builder.set_entry_point("collect_info")
builder.add_conditional_edges(
    "collect_info",
    lambda state: END if state.get('is_complete', False) else "collect_info"
)
graph = builder.compile()

__all__ = ["graph"]

# Async example runner
async def run_example():
    print("\n=== DEBUG: Starting Conversation ===")
    print(f"🤖 Using prompt type: {AGENT_PROMPT_TYPE}")
    
    user_email = input("Please enter your email address: ").strip()
    if not user_email:
        print("No email provided.")
        user_email = "test@example.com"

    first_input = {
        "user_input": "",
        "previous_state": None,
        "user_email": user_email
    }
    result = await process_message(first_input)
    print("\nAssistant:", result["question"])
    print(f"Turn: {result['turn_count']}")

    while not result["is_complete"]:
        user_input = input("You: ")
        next_input = {
            "user_input": user_input,
            "previous_state": {
                "conversation_history": result["conversation_history"],
                "is_complete": result["is_complete"],
                "turn_count": result["turn_count"],
                "user_email": result["user_email"]
            }
        }
        result = await process_message(next_input)
        print("\nAssistant:", result["question"])
        print(f"Turn: {result['turn_count']}")

    print("\n=== DEBUG: Conversation Complete ===")
    print(f"Final state: {result['completion_state']}")
    print(f"Total turns: {result['turn_count']}")
    print("\nFull Conversation History:")
    print(result["conversation_history"])

if __name__ == "__main__":
    asyncio.run(run_example())