# LangGraph Integration Guide

## Overview

Your cloud function has been updated to properly call your deployed `oneNodeRemMem` service using the `langgraph_sdk`, following the pattern from the working `gcp2langgraph` repository.

## Key Changes Made

### 1. Updated Cloud Function (`cloud_function/main.py`)

**Before:** The function was trying to call a local LangGraph server using `LANGGRAPH_SERVER_URL`

**After:** The function now properly calls your deployed LangGraph service using:
- `LANGGRAPH_DEPLOYMENT_URL` - Your deployed LangGraph service URL
- `LANGGRAPH_API_KEY` - Your LangGraph API key
- `langgraph_sdk` - The official SDK for calling deployed LangGraph services

### 2. Updated Requirements (`cloud_function/requirements.txt`)

Added the `langgraph_sdk` dependency:
```
langgraph_sdk>=0.4.5,<0.5.0
```

### 3. Improved Input/Output Handling

The cloud function now:
- Sends properly formatted input data matching `oneNodeRemMem` expectations
- Handles streaming responses from the deployed service
- Extracts the correct response format (question, conversation_history, is_complete, etc.)
- Provides better error handling and logging

## Environment Variables Required

You need to set these environment variables in your cloud function deployment:

```yaml
# In your .env.yaml file for deployment
LANGGRAPH_DEPLOYMENT_URL: "https://your-deployed-langgraph-url.us.langgraph.app"
LANGGRAPH_API_KEY: "lsv2_pt_your_langgraph_api_key"
```

## Testing Your Integration

### 1. Test the Deployed Service Directly

Run the test script to verify your deployed `oneNodeRemMem` service works:

```bash
./test_langgraph_deployment.sh
```

This will:
- Test the connection to your deployed service
- Send a sample input
- Show the streaming response
- Verify the response format

### 2. Test the Cloud Function Locally

You can test the cloud function locally using the Functions Framework:

```bash
cd cloud_function
functions-framework --target=process_email --debug --port=8080
```

Then send a test request:

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-firebase-token" \
  -d '{
    "userEmail": "test@example.com",
    "userResponse": "Yes, I am ready to discuss my task",
    "taskTitle": "Test Task"
  }'
```

## Deployment Steps

### 1. Update Environment Variables

Make sure your cloud function has the correct environment variables:

```bash
# Deploy with updated environment variables
gcloud functions deploy process-email \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=./cloud_function \
  --entry-point=process_email \
  --trigger-http \
  --timeout=540s \
  --memory=2048MB \
  --env-vars-file .env.yaml
```

### 2. Verify Deployment

After deployment, test the function with a real request to ensure it can properly call your deployed `oneNodeRemMem` service.

## Expected Flow

1. **User sends email response** → Cloud function receives request
2. **Cloud function calls deployed LangGraph** → Uses `langgraph_sdk` to call `oneNodeRemMem`
3. **LangGraph processes response** → Returns structured response with question, conversation history, etc.
4. **Cloud function handles response** → Updates Firestore, sends follow-up email if needed
5. **Process repeats** → Until conversation is complete

## Troubleshooting

### Common Issues

1. **"LANGGRAPH_DEPLOYMENT_URL not found"**
   - Check that you've set the environment variable correctly
   - Verify the URL format matches your LangGraph deployment

2. **"LANGGRAPH_API_KEY not found"**
   - Ensure your API key is set in the environment variables
   - Verify the API key is valid and has proper permissions

3. **"No response received from LangGraph"**
   - Check that your deployed service name matches "oneNodeRemMem"
   - Verify the input format matches what your service expects
   - Check the LangGraph deployment logs for errors

4. **Authentication errors**
   - Ensure your Firebase authentication is working
   - Check that the user email matches the authenticated user

### Debugging Tips

1. **Check Cloud Function Logs**
   ```bash
   gcloud functions logs read process-email --limit=50
   ```

2. **Test LangGraph Service Directly**
   ```bash
   ./test_langgraph_deployment.sh
   ```

3. **Verify Environment Variables**
   ```bash
   gcloud functions describe process-email --region=us-central1
   ```

## Next Steps

1. **Deploy your updated cloud function** with the new environment variables
2. **Test the integration** using the provided test scripts
3. **Monitor the logs** to ensure everything is working correctly
4. **Update your mobile app** to use the new cloud function endpoint

## Architecture Summary

```
Mobile App → Cloud Function → Deployed LangGraph (oneNodeRemMem) → Response
     ↓              ↓                    ↓
Firebase Auth   Firestore DB      Email Service
```

The cloud function now acts as a proper bridge between your mobile app and the deployed LangGraph service, handling authentication, state management, and email communication. 