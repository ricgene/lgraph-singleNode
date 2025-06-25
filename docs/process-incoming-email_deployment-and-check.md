# Function Purpose, Deployment, and Verification

## Purpose

This cloud function (`process-incoming-email`) manages the real estate concierge conversation loop for Prizm. It:
- Receives user email responses
- Maintains task-specific conversation state in Firestore
- Interacts with the deployed LangGraph agent (via the LANGGRAPH_SERVER_URL)
- Sends follow-up questions or completion emails to users
- Ensures each task is isolated by using a unique key: `taskAgent1-userEmail-taskTitle-taskCreateTimestamp`

## Deployment Steps

1. **Update Environment Variables**
   - Ensure `.env` and deployment command include:
     - `EMAIL_FUNCTION_URL` (for sending emails)
     - `LANGGRAPH_SERVER_URL` (for LangGraph agent endpoint)
     - `OPENAI_API_KEY` (for agent LLM)

2. **Deploy the Function**
   ```bash
   gcloud functions deploy process-incoming-email \
     --gen2 \
     --runtime=python311 \
     --region=us-central1 \
     --source=cloud_function \
     --entry-point=process_email_pubsub \
     --trigger-topic=incoming-messages \
     --memory=512MB \
     --timeout=540s \
     --set-env-vars EMAIL_FUNCTION_URL=https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple,LANGGRAPH_SERVER_URL=https://prizm2-9d0348d2abe5594d8b533da6f9b05cac.us.langgraph.app,OPENAI_API_KEY=your-key-here
   ```

3. **Verify Deployment**
   - Check the deployed function in the [Google Cloud Console](https://console.cloud.google.com/functions/details/us-central1/process-incoming-email?project=prizmpoc)
   - Confirm environment variables are set:
     ```bash
     gcloud functions describe process-incoming-email --region=us-central1 --format="value(serviceConfig.environmentVariables)"
     ```
   - Check logs for successful startup and processing:
     ```bash
     gcloud functions logs read process-incoming-email --region=us-central1 --limit=10
     ```

## Testing & Health Check

- **Send a test message:**
  ```bash
  curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email \
    -H "Content-Type: application/json" \
    -d '{"userEmail": "test@example.com", "userResponse": "Test message for task isolation", "taskTitle": "Test Task 1"}'
  ```
- **Check Firestore:**
  - Each task should have its own document in `taskAgent1` with a key like `taskAgent1_test@example.com_Test Task 1_<timestamp>`
  - Conversation history and state should be isolated per task

## Key Points

- **Task Isolation:** Each task is uniquely identified and stored
- **No Local Server Needed:** All processing is now handled by the deployed function and remote LangGraph agent
- **Easy Rollback:** Old data structure is still readable for backward compatibility

---
_Last updated: 2025-06-25_ 