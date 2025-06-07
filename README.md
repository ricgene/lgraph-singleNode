# LangGraph Agent ...

This project implements an intelligent agent using LangGraph and LangChain for conducting progressive questioning and determining outcomes based on user responses.

## Project Details

For a detailed walkthrough of the project architecture and implementation, visit:
[Project Architecture Documentation](https://claude.ai/share/ddd67875-08ab-40df-89a5-53a4edfed9f4)

The project demonstrates:
- State-based workflow using LangGraph
- Progressive questioning with memory retention
- Dynamic sub-question generation
- Real-time streaming responses
- Outcome determination based on collected information

## Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install python-dotenv langchain-openai langgraph
```

3. Set up your environment variables:
   - Copy `.env-example` to `.env`
   - Add your OpenAI API key to the `.env` file:
     ```
     OPENAI_API_KEY=your-api-key-here
     ```

## Usage

Run the agent:
```bash
python agent.py
```

## Features

- Progressive questioning with memory
- Sub-question handling for detailed information gathering
- Outcome determination based on collected information
- Streaming support for real-time responses
- State management using LangGraph

## Project Structure

The project uses LangGraph to create a state-based workflow that:
1. Conducts progressive questioning
2. Handles sub-questions for detailed information
3. Determines outcomes based on collected information
4. Provides real-time streaming responses

### Key Components

- **State Management**: Uses `AgentState` to track conversation history, memory, and progress
- **Question Flow**: Implements both main questions and dynamic sub-questions
- **Outcome Determination**: Analyzes collected information to determine the most appropriate outcome
- **Streaming Support**: Provides real-time response streaming for better user interaction

For more details about the implementation and architecture, please refer to the [Project Architecture Documentation](https://claude.ai/share/ddd67875-08ab-40df-89a5-53a4edfed9f4).

## Requirements

- Python 3.8+
- OpenAI API key
- Required Python packages (see setup instructions)

## Testing and Deployment

### Environment Variables

Ensure your `.env` file contains the necessary API keys:

- `OPENAI_API_KEY` (for OpenAI models)
- `LANGSMITH_API_KEY` (if using LangGraph Cloud or LangSmith)
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` (if using Langfuse)

### Dependencies

Install all required packages:

```bash
pip install langgraph langchain langchain_core python-dotenv
# Add any other dependencies you use (e.g., langchain_openai)
```

### Running Tests

You can run your script as is with `python your_script.py` or use `unittest` for automated tests:

```bash
python -m unittest unittest_agent2.py -v
```

### Testing with LangGraph Cloud (Optional)

If you want to test or deploy on LangGraph Cloud, follow the official guide:

1. Install the CLI:
   ```bash
   pip install -U "langgraph-cli[inmem]"
   ```

2. Set up your config and API keys.

You may need to adapt your entrypoint slightly for cloud deployment, but for local testing, your code is ready.

### Monitoring/Evaluation (Optional)

If you want to trace or evaluate your agent with Langfuse or LangSmith, you can add their handlers as callbacks when invoking the graph.

### Project Status

- `workflow2.did`: Deployed to cloud, but currently unused.
- `trace_example.py`: An unverified example.
- `agentOnWeb.py`: Unverified.

### References

- [LangGraph Cloud Deployment Guide](https://langchain-ai.github.io/langgraph/cloud/deployment/test_locally/)
- [LangGraph Agents Documentation](https://langchain-ai.github.io/langgraph/agents/agents/)
- [Langfuse Integration Example](https://langfuse.com/docs/integrations/langchain/example-langgraph-agents)
- [Zep LangGraph Tutorial](https://www.getzep.com/ai-agents/langgraph-tutorial) 
