from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import asyncio
from dotenv import load_dotenv
import os

# Load environment variables from .env file
try:
   load_dotenv()
except Exception as e:
    print(f"Error loading environment variables from .env: {str(e)}")

def test_api_key():
    """Test if the OpenAI API key is loaded correctly."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ OpenAI API key is loaded successfully")
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        print(f"API Key (masked): {masked_key}")
    else:
        print("❌ OpenAI API key is not loaded")
        print("Please make sure you have a .env file with OPENAI_API_KEY set")

test_api_key()
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Define the conversation state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    step: Literal["q1", "q2", "q3", "done"]

# Node: Ask first question
async def ask_q1(state: State):
    if "__resume" in state:
        user_input = state["__resume"]
        messages = [
            AIMessage(content="What is your account number?"),
            HumanMessage(content=user_input)
        ]
        # Call the LLM
        llm_response = await llm.ainvoke(messages)
        #llm_response = llm.invoke(messages)
        messages.append(AIMessage(content=llm_response.content))
        return {
            "messages": messages,
            "step": "q2"
        }
    else:
        question = "What is your account number?"
        return interrupt({"question": question})


# Node: Ask second question
async def ask_q2(state: State):
    if "__resume" in state:
        user_input = state["__resume"]
        # Append the user's answer
        messages = state["messages"] + [
            AIMessage(content="What issue are you experiencing?"),
            HumanMessage(content=user_input)
        ]
        # Call the LLM with the full conversation so far
        llm_response = await llm.ainvoke(messages)
        #llm_response = llm.invoke(messages)
        # Append the LLM's answer to the messages
        messages.append(AIMessage(content=llm_response.content))
        return {
            "messages": messages,
            "step": "q3"
        }
    else:
        question = "What issue are you experiencing?"
        return interrupt({"question": question})
    
async def ask_q3(state: State):
    if "__resume" in state:
        user_input = state["__resume"]
        # Append the user's answer
        messages = state["messages"] + [
            AIMessage(content="What is the date of the issue?"),
            HumanMessage(content=user_input)
        ]
        # Call the LLM with the full conversation so far
        llm_response = await llm.ainvoke(messages)
        #llm_response = llm.invoke(messages)
        # Append the LLM's answer to the messages
        messages.append(AIMessage(content=llm_response.content))
        return {
            "messages": messages,
            "step": "done"
        }
    else:
        question = "What is the date of the issue?"
        return interrupt({"question": question})

# Node: Complete the workflow
def finish(state: State):
    try:
        answers = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)][-3:]
        summary = (
            f"Thank you. To confirm, your account number is '{answers[0]}', "
            f"your issue is '{answers[1]}', and it started on '{answers[2]}'."
        )
        return {
            "messages": state["messages"] + [AIMessage(content=summary)],
            "step": "done"
        }
    except Exception as e:
        print(f"Error in finish: {str(e)}")
        raise

# Create the graph (export this function)
def create_workflow():
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
    return builder.compile()

# This is what you'll deploy to LangGraph Platform
#workflow = create_workflow()
# Compile the graph

workflow = create_workflow()

# Export the workflow for cloud deployment
__all__ = ["workflow"]

async def run_example():
    """Run an example conversation"""
    state = {"messages": [], "step": "q1"}
    user_answers = ["123456", "Cannot access my account", "Yesterday"]
    for answer in user_answers:
        result = await workflow.ainvoke(state)
        # Remove __interrupt__ before resuming
        state = {k: v for k, v in result.items() if k != "__interrupt__"}
        print("\n--- INTERRUPT ---")
        print("Interrupt payload:", result.get("__interrupt__"))
        state = result.copy()
        state["__resume"] = answer
    result = await workflow.ainvoke(state)
    print("\nFinal state:", result)
    if result.get("step") == "done" and result.get("messages"):
        print("\nSummary:", result["messages"][-1].content)
    else:
        print("\nNo summary available. Final state:", result)

if __name__ == "__main__":
    asyncio.run(run_example())
