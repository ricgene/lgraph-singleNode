import unittest
from unittest.mock import patch
import asyncio
from agent2 import graph  # Import the graph from agent2.py

# Assume your LangGraph agent code is imported and defines `graph`

class TestCustomerServiceAgent(unittest.TestCase):
    async def async_test_three_question_flow(self):
        # Predefine the user responses for each interrupt
        user_responses = [
            "123456",                   # Account number
            "Cannot access my account", # Issue
            "Yesterday"                 # When issue started
        ]

        # Create a mock interrupt function that returns the response from the payload
        async def mock_interrupt(payload):
            return user_responses.pop(0)

        # Patch the interrupt function
        with patch("langgraph.types.interrupt", side_effect=mock_interrupt):
            state = {"messages": [], "step": "q1"}
            while state["step"] != "done":
                state = await graph.ainvoke(state)
            
            # Extract the summary message from the last AIMessage
            ai_messages = [m for m in state["messages"] if hasattr(m, "content")]
            summary = ai_messages[-1].content
            self.assertIn("123456", summary)
            self.assertIn("Cannot access my account", summary)
            self.assertIn("Yesterday", summary)
            print(summary)  # For demonstration

    def test_three_question_flow(self):
        asyncio.run(self.async_test_three_question_flow())

if __name__ == "__main__":
    unittest.main()
