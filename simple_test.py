# simple_test.py
from agent import create_workflow

# Create the graph
graph = create_workflow()

# Initialize test state
state = {
    "messages": [],
    "internal_memory": {},
    "current_question": 0,
    "sub_question_context": None,
    "sub_question_count": 0,
    "answers": {},
    "questioning_complete": False,
    "outcome": "needs_more_info"
}

# Get initial message
initial_state = graph.invoke(state)
print("Initial message:", initial_state["messages"][-1].content)

# Test with a sample interaction
test_responses = [
    "I want to build a customer portal",
    "Within the next 2 months",
    "Around $50,000",
    "Yes, we tried building one in-house"
]

current_state = initial_state
for response in test_responses:
    print("\nUser:", response)
    current_state = graph.invoke(current_state, {"user_input": response})
    print("Agent:", current_state["messages"][-1].content)

print("\nFinal outcome:", current_state["outcome"])
print("Collected answers:", current_state["answers"])