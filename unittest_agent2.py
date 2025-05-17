import unittest
import asyncio
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage, AIMessage

# Define the conversation state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    step: Literal["q1", "q2", "q3", "done"]

# Node: Ask first question
def ask_q1(state: State):
    if "__resume" in state:
        user_input = state["__resume"]
        return {
            "messages": [AIMessage(content="What is your account number?"), HumanMessage(content=user_input)],
            "step": "q2"
        }
    else:
        question = "What is your account number?"
        return interrupt({"question": question})

# Node: Ask second question
def ask_q2(state: State):
    if "__resume" in state:
        user_input = state["__resume"]
        return {
            "messages": state["messages"] + [AIMessage(content="What issue are you experiencing?"), HumanMessage(content=user_input)],
            "step": "q3"
        }
    else:
        question = "What issue are you experiencing?"
        return interrupt({"question": question})

# Node: Ask third question
def ask_q3(state: State):
    if "__resume" in state:
        user_input = state["__resume"]
        return {
            "messages": state["messages"] + [AIMessage(content="When did this issue start?"), HumanMessage(content=user_input)],
            "step": "done"
        }
    else:
        question = "When did this issue start?"
        return interrupt({"question": question})

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

class TestCustomerServiceAgent(unittest.TestCase):
    def test_three_question_flow(self):
        asyncio.run(self.async_test_three_question_flow())

    async def async_test_three_question_flow(self):
        state = {"messages": [], "step": "q1"}
        user_answers = ["123456", "Cannot access my account", "Yesterday"]

        print("Initial state:", state)
        for answer in user_answers:
            print("\nInvoking graph with state:", state)
            result = await graph.ainvoke(state)
            print("\n--- INTERRUPT ---")
            print("Interrupt payload:", result.get("__interrupt__"))
            # Remove '__interrupt__' and inject '__resume'
            state = {k: v for k, v in result.items() if k != "__interrupt__"}
            state["__resume"] = answer
            print("\nUpdated state for next invoke:", state)

        # Final step (should be 'done')
        result = await graph.ainvoke(state)
        print("\nFinal state:", result)
        if result.get("step") == "done" and result.get("messages"):
            print("\nSummary:", result["messages"][-1].content)
