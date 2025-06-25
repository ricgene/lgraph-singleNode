#!/bin/bash

# Deploy the updated cloud function with proper LangGraph integration
echo "🚀 Deploying updated process-incoming-email function..."

gcloud functions deploy process-incoming-email \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=cloud_function \
  --entry-point=process_email \
  --trigger-http \
  --memory=512MB \
  --timeout=540s \
  --set-env-vars LANGGRAPH_DEPLOYMENT_URL=https://prizm2-9d0348d2abe5594d8b533da6f9b05cac.us.langgraph.app,LANGGRAPH_API_KEY=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,EMAIL_FUNCTION_URL=https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple

echo "✅ Deployment completed!"
echo ""
echo "🔍 To check the deployment:"
echo "gcloud functions describe process-incoming-email --region=us-central1"
echo ""
echo "📋 To view logs:"
echo "gcloud functions logs read process-incoming-email --limit=10 --region=us-central1"
echo ""
echo "🌐 Function URL:"
echo "https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email" 