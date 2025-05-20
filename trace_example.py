# trace_example.py
from agent_convo_node import create_workflow
from langchain.globals import set_debug

# Enable debug mode for tracing
set_debug(True)

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

# Get initial message and trace
initial_state = graph.invoke(state)
trace = graph.get_trace(initial_state)

print("Graph trace:")
for node in trace["nodes"]:
    print(f"Node: {node}")
for edge in trace["edges"]:
    print(f"Edge: {edge}")