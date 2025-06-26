#!/bin/bash

# Deployment script for process-incoming-email function with Pub/Sub trigger

set -e

echo "🚀 Deploying process-incoming-email function with Pub/Sub trigger..."

# Configuration
PROJECT_ID="prizmpoc"  # Change this to your project ID
REGION="us-central1"
FUNCTION_NAME="process-incoming-email"
TOPIC_NAME="incoming-messages"

# Check if required environment variables are set
if [ -z "$LANGGRAPH_DEPLOYMENT_URL" ]; then
    echo "❌ Error: LANGGRAPH_DEPLOYMENT_URL environment variable not set"
    exit 1
fi

if [ -z "$LANGGRAPH_API_KEY" ]; then
    echo "❌ Error: LANGGRAPH_API_KEY environment variable not set"
    exit 1
fi

echo "📋 Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Function: $FUNCTION_NAME"
echo "  Topic: $TOPIC_NAME"
echo "  LangGraph URL: $LANGGRAPH_DEPLOYMENT_URL"

# Set the project
echo "🔧 Setting project..."
gcloud config set project $PROJECT_ID

# Create Pub/Sub topic if it doesn't exist
echo "📨 Creating Pub/Sub topic if it doesn't exist..."
gcloud pubsub topics create $TOPIC_NAME --quiet || echo "Topic already exists"

# Deploy the function with Pub/Sub trigger
echo "📦 Deploying function..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=cloud_function \
    --entry-point=process_email_pubsub \
    --trigger-topic=$TOPIC_NAME \
    --memory=512MB \
    --timeout=540s \
    --set-env-vars="LANGGRAPH_DEPLOYMENT_URL=$LANGGRAPH_DEPLOYMENT_URL,LANGGRAPH_API_KEY=$LANGGRAPH_API_KEY" \
    --allow-unauthenticated

echo "✅ Function deployed successfully!"

# Get the function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --gen2 --format="value(serviceConfig.uri)")

echo "🌐 Function URL: $FUNCTION_URL"

# Test the deployment
echo "🧪 Testing deployment..."
echo "You can test the function by:"
echo "1. Sending an email to the monitored Gmail account"
echo "2. Or running: python test_foilboi_workflow.py"

echo "📝 Next steps:"
echo "1. Make sure the email-watcher function is deployed and running"
echo "2. Send an email from foilboi@gmail.com to trigger the workflow"
echo "3. Check the function logs: gcloud functions logs read $FUNCTION_NAME --region=$REGION"

echo "🎯 Deployment complete!" 