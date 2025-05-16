# LangGraph Agent

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