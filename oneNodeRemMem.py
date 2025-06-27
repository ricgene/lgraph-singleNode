import os
import sys
import json
import logging
import asyncio
from typing import Dict, Optional
from dotenv import load_dotenv

import httpx  # Async HTTP client
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

def test_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.info("✅ OpenAI API key loaded")
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        logger.info(f"API Key (masked): {masked_key}")
    else:
        logger.error("❌ OPENAI_API_KEY missing")

test_api_key()

class DeckState:
    def __init__(self):
        self.conversation_history = ""
        self.all_info_collected = False
        self.is_complete = False
        self.turn_count = 0
        self.user_email = ""

    def __str__(self):
        return f"DeckState(conversation_history={self.conversation_history}, is_complete={self.is_complete}, turn_count={self.turn_count}, user_email={self.user_email})"

    def __repr__(self):
        return self.__str__()

llm = ChatOpenAI(model="gpt-4", temperature=0)
tracer = LangChainTracer()
console_handler = ConsoleCallbackHandler()
CALLBACKS = [tracer, console_handler]

async def send_email(recipient_email: str, subject: str, body: str) -> bool:
    """
    Send an email asynchronously.
    """
    try:
        email_function_url = os.getenv("EMAIL_FUNCTION_URL")
        if not email_function_url:
            logger.error("❌ EMAIL_FUNCTION_URL not found in environment variables")
            return False
        payload = {
            "to": recipient_email,
            "subject": subject,
            "body": body
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(email_function_url, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info(f"✅ Email sent successfully to {recipient_email}")
            return True
        else:
            logger.error(f"❌ Email function returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending email: {str(e)}")
        return False

async def process_message(input_dict: Dict) -> Dict:
    """
    Async version of process_message for LangGraph.
    """
    # Extract input values
    #user_input = input_dict.get('user_input', '')
    if isinstance(input_dict, dict):
        user_input = input_dict.get('user_input', '')
    else:
        user_input = getattr(input_dict, 'user_input', '')

    #previous_state = input_dict.get('previous_state', None)
    if isinstance(input_dict, dict):
        previous_state = input_dict.get('previous_state', None)
    else:
        previous_state = getattr(input_dict, 'previous_state', None)

    #user_email = input_dict.get('user_email', '')
    if isinstance(input_dict, dict):
        user_email = input_dict.get('user_email', '')
    else:
        user_email = getattr(input_dict, 'user_email', '')

    # Initialize or restore state
    if previous_state is None:
        state = DeckState()
        state.user_email = user_email
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

    turn_count = state.conversation_history.count("Question:")

    # Check for max turns
    if turn_count >= 7:
        state.is_complete = True
        final_message = "Thank you for your time. We've reached the maximum number of turns for this conversation."
        if state.user_email:
            await send_email(state.user_email, "Prizm Task Conversation Complete", final_message)
        return {
            "question": final_message,
            "conversation_history": state.conversation_history,
            "is_complete": True,
            "completion_state": "OTHER",
            "user_email": state.user_email
        }

    # Build system prompt
    system_prompt = f"""You are a helpful AI Agent named Helen helping a customer complete a home Task for Prizm Real Estate Concierge Service.
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
6. Current turn count: {turn_count}/7. You have {7 - turn_count} turns remaining."""

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    if state.conversation_history:
        messages.append({"role": "assistant", "content": state.conversation_history})
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

    if question:
        state.conversation_history += f"\nQuestion: {question}"
    if learned:
        state.conversation_history += f"\nLearned: {learned}"

    is_complete = "TASK_PROGRESSING" in response_text or "TASK_ESCALATION" in response_text
    if not is_complete and state.conversation_history:
        is_complete = "TASK_PROGRESSING" in state.conversation_history or "TASK_ESCALATION" in state.conversation_history
    state.is_complete = is_complete

    completion_state = "OTHER"
    if "TASK_PROGRESSING" in response_text or "TASK_PROGRESSING" in state.conversation_history:
        completion_state = "TASK_PROGRESSING"
    elif "TASK_ESCALATION" in response_text or "TASK_ESCALATION" in state.conversation_history:
        completion_state = "TASK_ESCALATION"

    # Email logic
    if is_complete:
        question = ""
        if state.user_email and "Thank you for selecting Prizm" not in state.conversation_history:
            await send_email(
                state.user_email,
                "Prizm Task Conversation Complete",
                "Thank you for your time. We've completed our conversation about your task."
            )
    elif state.user_email and question and not is_complete:
        email_body = f"""Hello!

Helen from Prizm here. I have a question for you about your task:

{question}

Please reply to this email with your response.

Best regards,
Helen
Prizm Real Estate Concierge Service"""
        await send_email(
            state.user_email,
            f"Prizm Task Question",
            email_body
        )

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
    lambda state: END  # Always transition to END
)
graph = builder.compile()

__all__ = ["graph"]

# Async example runner
async def run_example():
    print("\n=== DEBUG: Starting Conversation ===")
    user_email = input("Please enter your email address: ").strip()
    if not user_email:
        print("No email provided. Email functionality will be disabled.")
        user_email = ""

    first_input = {
        "user_input": "",
        "previous_state": None,
        "user_email": user_email
    }
    result = await process_message(first_input)
    print("\nAssistant:", result["question"])

    user_input = input("You: ")
    second_input = {
        "user_input": user_input,
        "previous_state": {
            "conversation_history": result["conversation_history"],
            "all_info_collected": False,
            "user_email": result["user_email"]
        }
    }
    result = await process_message(second_input)
    print("\nAssistant:", result["question"])

    q = 3
    while not result["is_complete"]:
        user_input = input("You: ")
        next_input = {
            "user_input": user_input,
            "previous_state": {
                "conversation_history": result["conversation_history"],
                "all_info_collected": False,
                "user_email": result["user_email"]
            }
        }
        result = await process_message(next_input)
        print("\nAssistant:", result["question"])
        q += 1

    print("\n=== DEBUG: Conversation Complete ===")
    print("\nFull Conversation History:")
    print(result["conversation_history"])

if __name__ == "__main__":
    asyncio.run(run_example())
