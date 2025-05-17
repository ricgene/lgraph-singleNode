import unittest
import asyncio
from agent2 import graph, State
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

class TestCustomerServiceAgent(unittest.TestCase):
    async def async_test_three_question_flow(self):
        # Start with initial state
        state = {"messages": [], "step": "q1"}
        print("\nInitial state:", state)
        user_answers = ["123456", "Cannot access my account", "Yesterday"]

        for answer in user_answers:
            # Run until interrupt
            result = await graph.ainvoke(state)
            print("\n--- INTERRUPT ---")
            print("Interrupt payload:", result.get("__interrupt__"))
            # Resume: inject answer into state
            state = result.copy()
            state["__resume"] = answer

        # Final step (should be 'done')
        result = await graph.ainvoke(state)
        print("\nFinal state:", result)
        print("\nSummary:", result["messages"][-1].content)
        self.assertEqual(result["step"], "done")
        self.assertEqual(len(result["messages"]), 7)  # Previous + summary
        self.assertIn("thank you", result["messages"][-1].content.lower())

    def test_three_question_flow(self):
        asyncio.run(self.async_test_three_question_flow())

if __name__ == "__main__":
    unittest.main()
