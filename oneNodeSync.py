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

class DeckMemory:
    def __init__(self, collected_info: Optional[Dict[str, str]] = None, conversation_history: Optional[List[Dict[str, str]]] = None):
        self.collected_info = collected_info or {
            "size": None,
            "materials": None,
            "budget": None,
            "timeline": None,
            "permit_requirements": None
        }
        self.conversation_history = conversation_history or []
    
    def to_dict(self) -> Dict:
        """Convert memory to dictionary for serialization"""
        return {
            "collected_info": self.collected_info,
            "conversation_history": self.conversation_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DeckMemory':
        """Create memory instance from dictionary"""
        return cls(
            collected_info=data.get("collected_info"),
            conversation_history=data.get("conversation_history")
        )
    
    def update_info(self, user_input: str):
        """Update collected information based on user input"""
        user_input = user_input.lower()
        if "size" in user_input or "dimension" in user_input:
            self.collected_info["size"] = user_input
        if "material" in user_input or "wood" in user_input:
            self.collected_info["materials"] = user_input
        if "budget" in user_input or "$" in user_input:
            self.collected_info["budget"] = user_input
        if "timeline" in user_input or "time" in user_input:
            self.collected_info["timeline"] = user_input
        if "permit" in user_input:
            self.collected_info["permit_requirements"] = user_input
    
    def get_missing_info(self) -> List[str]:
        """Return list of information that still needs to be collected"""
        return [key for key, value in self.collected_info.items() if value is None]
    
    def is_complete(self) -> bool:
        """Check if all required information has been collected"""
        return all(value is not None for value in self.collected_info.values())
    
    def get_summary(self) -> str:
        """Get a summary of collected information"""
        summary = "Collected Information:\n"
        for key, value in self.collected_info.items():
            if value:
                summary += f"{key}: {value}\n"
        return summary

class DeckState(TypedDict, total=False):
    conversation_history: List[Dict[str, str]]
    all_info_collected: bool
    last_assistant_message: str
    memory: Dict  # Store memory as dict for serialization

llm = ChatOpenAI(model="gpt-4", temperature=0)

def collect_deck_info(state: DeckState) -> DeckState:
    # Get memory from state and convert to DeckMemory object
    memory_dict = state.get("memory", {})
    memory = DeckMemory.from_dict(memory_dict)

    # Build the system prompt with current memory state
    system_prompt = """
You are a helpful assistant helping a user plan a new back deck project.
You need to gather the following information:
1. Deck size
2. Materials
3. Budget
4. Timeline
5. Permit requirements

IMPORTANT: If this is the first message (no conversation history), start by asking about the deck size.
Do not start with greetings or introductions. Be direct and ask for the first piece of information needed.

"""
    # Add memory summary to the prompt
    system_prompt += memory.get_summary()
    
    # Add missing information to the prompt
    missing_info = memory.get_missing_info()
    if missing_info:
        system_prompt += "\nStill need to collect:\n"
        for info in missing_info:
            system_prompt += f"- {info}\n"
    
    # Build the messages list
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history if it exists
    if memory.conversation_history:
        messages.extend(memory.conversation_history)
    
    # Add the last user response if it exists
    if state.get("user_response"):
        messages.append({"role": "user", "content": state["user_response"]})
        # Update memory with new information
        memory.update_info(state["user_response"])
        # Add to conversation history
        memory.conversation_history.append({"role": "user", "content": state["user_response"]})

    # ---- DEBUG PRINT ----
    print("\n=== DEBUG: State at Start of Turn ===")
    print("Memory Summary:")
    print(memory.get_summary())
    print("\nMissing Information:")
    print(memory.get_missing_info())
    print("\nMessages being sent to LLM:")
    print(json.dumps(messages, indent=2))
    print("=== END DEBUG ===\n")
    # ---------------------

    response = llm.invoke(messages)
    response_text = response.content
    
    # Add assistant's response to conversation history
    memory.conversation_history.append({"role": "assistant", "content": response_text})

    # Convert memory back to dict for state
    memory_dict = memory.to_dict()

    if memory.is_complete():
        return {
            "conversation_history": memory.conversation_history,
            "all_info_collected": True,
            "memory": memory_dict
        }
    else:
        return interrupt({
            "question": response_text,
            "conversation_history": memory.conversation_history,
            "last_assistant_message": response_text,
            "memory": memory_dict
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
        previous_state: The previous state (if any)
    
    Returns:
        Dict containing:
        - question: The assistant's response (if conversation continues)
        - memory: The updated memory state
        - conversation_history: The full conversation history
        - is_complete: Whether the conversation is complete
    """
    # Initialize or use previous state
    state = previous_state or {
        "conversation_history": [],
        "all_info_collected": False,
        "last_assistant_message": None,
        "memory": DeckMemory().to_dict()
    }
    
    # Add user input to state
    state["user_response"] = user_input
    
    # Process the message
    result = graph.invoke(state)
    
    # Check if conversation is complete
    if not result.get("__interrupt__"):
        return {
            "question": "Conversation complete!",
            "memory": result["memory"],
            "conversation_history": result["conversation_history"],
            "is_complete": True
        }
    
    # Get the interrupt payload
    interrupt_payload = result["__interrupt__"][0].value
    
    # Return the updated state
    return {
        "question": interrupt_payload["question"],
        "memory": interrupt_payload["memory"],
        "conversation_history": interrupt_payload["conversation_history"],
        "is_complete": False
    }

def start_conversation() -> Dict:
    """
    Start a new conversation by getting the initial greeting from the assistant.
    Returns the initial state that can be used for subsequent messages.
    """
    # Create initial state with empty memory
    state = {
        "conversation_history": [],
        "all_info_collected": False,
        "last_assistant_message": None,
        "memory": DeckMemory().to_dict()
    }
    
    # Process an empty message to get the initial greeting
    result = graph.invoke(state)
    
    # Get the interrupt payload with the initial greeting
    interrupt_payload = result["__interrupt__"][0].value
    
    return {
        "question": interrupt_payload["question"],
        "memory": interrupt_payload["memory"],
        "conversation_history": interrupt_payload["conversation_history"],
        "is_complete": False
    }

def run_example():
    """Example of how to use the process_message function"""
    # Start the conversation
    print("Starting conversation...")
    result = start_conversation()
    print("\nAssistant:", result["question"])
    
    # Initialize state for subsequent messages
    state = {
        "conversation_history": result["conversation_history"],
        "last_assistant_message": result["question"],
        "memory": result["memory"]
    }
    
    while True:
        user_input = input("You: ")
        result = process_message(user_input, state)
        
        print("\nAssistant:", result["question"])
        
        if result["is_complete"]:
            print("\nConversation complete!")
            print("\nFinal Deck Information:")
            memory = DeckMemory.from_dict(result["memory"])
            print(memory.get_summary())
            print("\nFull Conversation:")
            for msg in result["conversation_history"]:
                role = msg["role"].capitalize()
                print(f"{role}: {msg['content']}")
            break
        
        # Update state for next iteration
        state = {
            "conversation_history": result["conversation_history"],
            "last_assistant_message": result["question"],
            "memory": result["memory"]
        }

if __name__ == "__main__":
    run_example()
