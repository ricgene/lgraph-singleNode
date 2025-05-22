

# LangGraph Agent - Google Cloud Function Deployment

Deploy your LangGraph agent as a synchronous Google Cloud Function that handles human-in-the-loop (HITL) interactions.

Related perpliexity like:
https://www.perplexity.ai/search/call-langsmith-from-gcp-SUeirpGwS..iQt1Wb6WiPw?login-new=false&login-source=visitorGate

## Overview

This implementation provides a production-ready deployment of a LangGraph agent on Google Cloud Platform using Cloud Functions. It supports stateful conversations with human-in-the-loop capabilities, making it ideal for interactive AI workflows that require user input at specific decision points.

## Features

- **State Management**: Maintains conversation state between turns
- **Error Handling**: Returns proper HTTP status codes
- **Synchronous Flow**: Works with GCP's request-response model
- **Security**: Uses environment variables for credentials
- **HITL Support**: Built for human-in-the-loop workflows

## Prerequisites

- Google Cloud Platform account
- `gcloud` CLI installed and configured
- LangGraph deployment URL
- LangSmith API key

## Cloud Function Code

Create a `main.py` file with the following content:

```python
from langgraph_sdk import get_sync_client
from dotenv import load_dotenv
import os
import json

load_dotenv()

def langgraph_agent(request):
    """HTTP Cloud Function to handle LangGraph agent interactions"""
    client = get_sync_client(
        url=os.getenv("LANGGRAPH_DEPLOYMENT_URL"),
        api_key=os.getenv("LANGSMITH_API_KEY")
    )

    # Parse request data
    request_data = request.get_json()
    is_new_conversation = request_data.get("new_conversation", True)
    user_input = request_data.get("user_input", "")
    previous_state = request_data.get("state", {})

    try:
        if is_new_conversation:
            # Start new conversation
            result = client.runs.invoke(
                None,
                "superNode",  # Your workflow name
                input={
                    "messages": [],
                    "step": "q1",
                    "iteration": 0
                }
            )
        else:
            # Resume existing conversation
            result = client.runs.invoke(
                None,
                "superNode",
                input={
                    **previous_state,
                    "__resume__": user_input
                }
            )

        if "__interrupt__" in result:
            return {
                "question": result["__interrupt__"][0].value["question"],
                "state": {k: v for k, v in result.items() if k != "__interrupt__"},
                "completed": False
            }, 200
        else:
            return {
                "response": result.get("messages", [])[-1].content if result.get("messages") else "Done",
                "completed": True
            }, 200

    except Exception as e:
        return {"error": str(e)}, 500
```

## Setup Files

### requirements.txt

```text
langgraph-sdk
python-dotenv
flask>=2.0.0
functions-framework==3.*
```

### .env

```bash
LANGGRAPH_DEPLOYMENT_URL="your-deployment-url"
LANGSMITH_API_KEY="your-langsmith-api-key"
```

## Deployment

Deploy the function to Google Cloud Platform:

```bash
gcloud functions deploy langgraph-agent \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --env-vars-file .env \
  --timeout 540s
```

## Usage

### Starting a New Conversation

```bash
curl -X POST YOUR_FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{"new_conversation": true}'
```

**Response:**
```json
{
  "question": "What is your account number?",
  "state": {...}, 
  "completed": false
}
```

### Submitting User Input

```bash
curl -X POST YOUR_FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{
    "new_conversation": false,
    "user_input": "12345",
    "state": {...}  # From previous response
  }'
```

## Request/Response Format

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_conversation` | boolean | Yes | `true` to start new conversation, `false` to continue |
| `user_input` | string | No | User's response (required when `new_conversation` is `false`) |
| `state` | object | No | Previous conversation state (required when continuing) |

### Response Body

**During Conversation (HITL):**
```json
{
  "question": "Next question for the user",
  "state": {...},
  "completed": false
}
```

**Conversation Complete:**
```json
{
  "response": "Final response from agent",
  "completed": true
}
```

**Error:**
```json
{
  "error": "Error message"
}
```

## Production Considerations

### Security
- Remove `--allow-unauthenticated` flag and implement proper authentication
- Use IAM roles and service accounts for access control
- Validate and sanitize all input data

### State Management
- Implement persistent state storage using Firestore or Redis
- Avoid passing large state objects in requests
- Consider state expiration and cleanup

### Monitoring & Logging
- Enable Cloud Monitoring for performance metrics
- Set up structured logging for debugging
- Implement health checks and alerting

### Performance & Reliability
- Add rate limiting and quotas
- Configure appropriate timeout values
- Implement retry logic for external API calls
- Use connection pooling for database connections

### Scaling
- Monitor function invocation metrics
- Consider using Cloud Run for more control over scaling
- Implement caching strategies for frequently accessed data

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `LANGGRAPH_DEPLOYMENT_URL` | URL of your deployed LangGraph instance | Yes |
| `LANGSMITH_API_KEY` | API key for LangSmith authentication | Yes |

## Error Handling

The function returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `500`: Internal Server Error

## Local Development

For local testing, you can use the Functions Framework:

```bash
pip install functions-framework
functions-framework --target=langgraph_agent --debug
```

## Troubleshooting

### Common Issues

1. **Function timeout**: Increase timeout value or optimize agent response time
2. **Memory issues**: Monitor memory usage and increase allocation if needed
3. **Environment variables not loaded**: Ensure `.env` file is properly configured
4. **Authentication errors**: Verify API keys and deployment URLs

### Debugging

Enable debug logging by setting environment variables:
```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export FUNCTION_NAME=langgraph-agent
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review Google Cloud Functions documentation
- Open an issue in the repository