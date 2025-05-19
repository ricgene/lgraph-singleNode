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

# Test API key
def test_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✅ OpenAI API key is loaded successfully")
        print(f"API Key (masked): {api_key[:4]}...{api_key[-4:]}")
    else:
        print("❌ OpenAI API key is not loaded")

test_api_key()

# Initialize the model
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Define the conversation state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    step: Literal["q1", "q2", "q3", "done"]

# Question nodes (only interrupt)
async def ask_q1(state: State):
    return interrupt({"question": "What is your account number?"})

async def ask_q2(state: State):
    return interrupt({"question": "What issue are you experiencing?"})

async def ask_q3(state: State):
    return interrupt({"question": "What is the date of the issue?"})

# Resume handler to process user input
async def handle_resume(state: State):
    user_input = state["__resume"]
    messages = state["messages"]
    step = state["step"]

    if step == "q1":
        messages += [
            AIMessage(content="What is your account number?"),
            HumanMessage(content=user_input)
        ]
        response = await llm.ainvoke(messages)
        messages.append(AIMessage(content=response.content))
        return {"messages": messages, "step": "q2"}

    elif step == "q2":
        messages += [
            AIMessage(content="What issue are you experiencing?"),
            HumanMessage(content=user_input)
        ]
        response = await llm.ainvoke(messages)
        messages.append(AIMessage(content=response.content))
        return {"messages": messages, "step": "q3"}

    elif step == "q3":
        messages += [
            AIMessage(content="What is the date of the issue?"),
            HumanMessage(content=user_input)
        ]
        response = await llm.ainvoke(messages)
        messages.append(AIMessage(content=response.content))
        return {"messages": messages, "step": "done"}

    else:
        return {"messages": messages}

# Final node: summarize
def finish(state: State):
    try:
        human_msgs = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if len(human_msgs) < 3:
            raise ValueError("Not enough answers to summarize.")
        answers = human_msgs[-3:]
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
        return {
            "messages": state.get("messages", []) + [AIMessage(content="Sorry, I couldn't generate the summary.")],
            "step": "done"
        }

# Build the workflow graph
def create_workflow():
    builder = StateGraph(State)
    builder.add_node("ask_q1", ask_q1)
    builder.add_node("ask_q2", ask_q2)
    builder.add_node("ask_q3", ask_q3)
    builder.add_node("resume", handle_resume)
    builder.add_node("finish", finish)

    builder.set_entry_point("ask_q1")

    builder.add_edge("ask_q1", "resume")
    builder.add_edge("resume", "ask_q2")
    builder.add_edge("ask_q2", "resume")
    builder.add_edge("resume", "ask_q3")
    builder.add_edge("ask_q3", "resume")
    builder.add_edge("resume", "finish")
    builder.add_edge("finish", END)

    return builder.compile()

# Deployable object
workflow = create_workflow()
__all__ = ["workflow"]

# Optional: local test
async def run_example():
    state = {"messages": [], "step": "q1"}
    user_inputs = ["123456", "Cannot access my account", "Yesterday"]

    for user_input in user_inputs:
        result = await workflow.ainvoke(state)
        print("\n--- INTERRUPT ---")
        print("Interrupt payload:", result.get("__interrupt__"))
        state = {k: v for k, v in result.items() if k != "__interrupt__"}
        state["__resume"] = user_input

    result = await workflow.ainvoke(state)
    print("\nFinal state:", result)
    if result.get("step") == "done":
        print("\nSummary:", result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(run_example())
