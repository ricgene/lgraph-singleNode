from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt.interrupt import HumanInterrupt
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def test_api_key():
    """Test if the OpenAI API key is loaded correctly."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ OpenAI API key is loaded successfully")
        # Print first 4 and last 4 characters of the key for verification
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        print(f"API Key (masked): {masked_key}")
    else:
        print("❌ OpenAI API key is not loaded")
        print("Please make sure you have a .env file with OPENAI_API_KEY set")

# Define the conversation state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    step: Literal["q1", "q2", "q3", "done"]

# Node: Ask first question
def ask_q1(state: State):
    question = "What is your account number?"
    interrupt = HumanInterrupt(question)
    user_input = interrupt.get_response()
    return {
        "messages": [AIMessage(content=question), HumanMessage(content=user_input)],
        "step": "q2"
    }

# Node: Ask second question
def ask_q2(state: State):
    question = "What issue are you experiencing?"
    interrupt = HumanInterrupt(question)
    user_input = interrupt.get_response()
    return {
        "messages": [AIMessage(content=question), HumanMessage(content=user_input)],
        "step": "q3"
    }

# Node: Ask third question
def ask_q3(state: State):
    question = "When did this issue start?"
    interrupt = HumanInterrupt(question)
    user_input = interrupt.get_response()
    return {
        "messages": [AIMessage(content=question), HumanMessage(content=user_input)],
        "step": "done"
    }

# Node: Complete the workflow
def finish(state: State):
    answers = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)][-3:]
    summary = (
        f"Thank you. To confirm, your account number is '{answers[0]}', "
        f"your issue is '{answers[1]}', and it started on '{answers[2]}'."
    )
    return {
        "messages": [AIMessage(content=summary)],
        "step": "done"
    }

# Build the graph
builder = StateGraph(State)
builder.add_node("ask_q1", ask_q1)
builder.add_node("ask_q2", ask_q2)
builder.add_node("ask_q3", ask_q3)
builder.add_node("finish", finish)
builder.set_entry_point("ask_q1")
builder.add_edge("ask_q1", "ask_q2")
builder.add_edge("ask_q2", "ask_q3")
builder.add_edge("ask_q3", "finish")
builder.add_edge("finish", END)
graph = builder.compile()

async def run_example():
    """Run an example conversation"""
    state = {"messages": [], "step": "q1"}
    result = await graph.ainvoke(state)
    print("Final state:", result)

if __name__ == "__main__":
    asyncio.run(run_example())
