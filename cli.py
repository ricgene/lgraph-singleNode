from agent2 import graph
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
import logging
import traceback
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Maximum number of iterations to prevent infinite loops
MAX_ITERATIONS = 10

def create_initial_state() -> Dict[str, Any]:
    """Create a new initial state for the agent"""
    return {
        "messages": [],
        "step": "q1"
    }

async def get_user_input(prompt: str) -> str:
    """Get user input with a prompt"""
    print(prompt)
    return input("> ")

async def main():
    try:
        state = create_initial_state()
        iteration_count = 0
        
        while state["step"] != "done" and iteration_count < MAX_ITERATIONS:
            try:
                # Process with graph
                logger.debug(f"Current state before processing: {state}")
                state = await graph.ainvoke(state)
                logger.debug(f"New state after processing: {state}")
                
                # Print AI response
                if state["messages"] and len(state["messages"]) > 0:
                    print(state["messages"][-1].content)
                
                iteration_count += 1
                
            except Exception as e:
                logger.error(f"Error during conversation: {str(e)}")
                logger.error(traceback.format_exc())
                print("Sorry, something went wrong. Please try again.")
                continue
        
        if iteration_count >= MAX_ITERATIONS:
            print("\nError: Maximum number of iterations reached. The conversation may be stuck in a loop.")
            return
            
        # Print final outcome
        print("\nQuestionnaire complete!")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.error(traceback.format_exc())
        print("A fatal error occurred. Please check the logs for details.")

if __name__ == "__main__":
    asyncio.run(main()) 