from typing import TypedDict, List, Dict, Optional
from langchain_openai import ChatOpenAI
import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Force new deployment - updated API key
# In cloud functions, environment variables are set via deployment
# No need to load from .env file

# --- Dependencies for the agent ---

llm = ChatOpenAI(model="gpt-4", temperature=0)

class DeckState:
    """A class to hold the state of the conversation."""
    def __init__(self):
        self.conversation_history = ""
        self.is_complete = False
        self.user_email = ""

def send_email_via_gcp(recipient_email: str, subject: str, body: str) -> bool:
    """Sends an email by calling the deployed GCP email function."""
    # Use the environment variable for the email function URL
    email_function_url = os.getenv('EMAIL_FUNCTION_URL', 'https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple')
    if not email_function_url:
        logger.error("❌ EMAIL_FUNCTION_URL not found in environment variables.")
        return False
    try:
        payload = {"to": recipient_email, "subject": subject, "body": body}
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

# --- Core Agent Logic ---

def run_agent_turn(user_input: str, previous_state: Optional[Dict] = None, user_email: str = "") -> Dict:
    """
    Processes a single turn of the conversation in a stateless manner.
    """
    # Initialize or restore state
    state = DeckState()
    if previous_state:
        state.conversation_history = previous_state.get('conversation_history', '')
        state.is_complete = previous_state.get('is_complete', False)
        state.user_email = previous_state.get('user_email', user_email)
    else:
        state.user_email = user_email

    turn_count = state.conversation_history.count("Question:")

    if turn_count >= 7:
        state.is_complete = True
        final_message = "Thank you for your time. We've reached the maximum number of turns for this conversation."
        if state.user_email:
            send_email_via_gcp(state.user_email, "Prizm Task Conversation Complete", final_message)
        return {
            "question": final_message,
            "conversation_history": state.conversation_history,
            "is_complete": True,
            "user_email": state.user_email
        }

    # Build system prompt
    system_prompt = f"""You are a helpful AI Agent named Helen is helping a customer complete a home Task. You work for Prizm which is a Real Estate Concierge Service.
    You need to collect the following information:
    1. Are they ready to discuss their Task?
    2. Will they reach out to the contractor <C>?
    3. Do they have any concerns or questions?

    Format your responses as:
    Question: [Your next question]
    Learned: [What you've learned from the conversation so far]
    
    IMPORTANT RULES:
    1. ALWAYS format your response with "Question:" and "Learned:" sections.
    2. If the user's response is unclear, rephrase your question to be more specific and note that in the "Learned" section.
    3. Start by asking about point 1 if no information has been provided.
    4. After each response, assess what new information you've learned.
    5. When you have all information, end with 'TASK_PROGRESSING' if the user will move forward, otherwise 'TASK_ESCALATION'.
    6. Current turn count: {turn_count}/7. You have {7 - turn_count} turns remaining."""

    # Build message list
    messages = [{"role": "system", "content": system_prompt}]
    if state.conversation_history:
        # Simplified history for the model
        history_for_prompt = state.conversation_history.replace("Agent:", "assistant:").replace("User:", "user:")
        messages.append({"role": "assistant", "content": history_for_prompt})
    if user_input:
        messages.append({"role": "user", "content": user_input})

    # Invoke the language model
    try:
        response = llm.invoke(messages)
        agent_response_text = response.content
    except Exception as e:
        logger.error(f"Error invoking LLM: {e}")
        agent_response_text = "I'm sorry, I encountered an issue. Could you please repeat that?"

    # Update conversation history
    new_history_entry = f"User: {user_input}\nAgent: {agent_response_text}\n"
    state.conversation_history += new_history_entry
    
    # Check for completion keywords
    if "TASK_PROGRESSING" in agent_response_text or "TASK_ESCALATION" in agent_response_text:
        state.is_complete = True

    # Parse the "Question:" part for the return value
    question_part = agent_response_text.split("Question:")[-1].split("Learned:")[0].strip()

    return {
        "question": question_part,
        "conversation_history": state.conversation_history,
        "is_complete": state.is_complete,
        "user_email": state.user_email
    } 