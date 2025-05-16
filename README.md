# LangGraph Agent

This project implements an intelligent agent using LangGraph and LangChain for conducting progressive questioning and determining outcomes based on user responses.

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

## Project Details

For more information about the project architecture and implementation, visit:
https://claude.ai/share/ddd67875-08ab-40df-89a5-53a4edfed9f4

## Features

- Progressive questioning with memory
- Sub-question handling for detailed information gathering
- Outcome determination based on collected information
- Streaming support for real-time responses
- State management using LangGraph

## Requirements

- Python 3.8+
- OpenAI API key
- Required Python packages (see setup instructions) 