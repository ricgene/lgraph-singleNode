#!/bin/bash

# Deploy Telegram Bot Cloud Function
# This script deploys the Telegram webhook handler to Google Cloud Functions

set -e

echo "🚀 Deploying Telegram Bot Cloud Function..."

# Configuration
FUNCTION_NAME="telegram-webhook"
REGION="us-central1"
SOURCE_DIR="telegram_function"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory $SOURCE_DIR not found"
    exit 1
fi

# Check if required files exist
if [ ! -f "$SOURCE_DIR/main.py" ]; then
    echo "❌ main.py not found in $SOURCE_DIR"
    exit 1
fi

if [ ! -f "$SOURCE_DIR/requirements.txt" ]; then
    echo "❌ requirements.txt not found in $SOURCE_DIR"
    exit 1
fi

# Deploy the Cloud Function
echo "📦 Deploying function from $SOURCE_DIR..."

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=$SOURCE_DIR \
    --entry-point=telegram_webhook \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},LANGGRAPH_DEPLOYMENT_URL=${LANGGRAPH_DEPLOYMENT_URL},LANGGRAPH_API_KEY=${LANGGRAPH_API_KEY}" \
    --timeout=60s \
    --memory=256MB

if [ $? -eq 0 ]; then
    echo "✅ Telegram webhook function deployed successfully!"
    
    # Get the function URL
    FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(serviceConfig.uri)")
    echo "📡 Function URL: $FUNCTION_URL"
    
    # Optionally set the webhook automatically if TELEGRAM_BOT_TOKEN is set
    if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo "🔧 Setting Telegram webhook..."
        curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
             -H "Content-Type: application/json" \
             -d "{\"url\": \"$FUNCTION_URL\"}"
        echo ""
        echo "✅ Webhook configured!"
    else
        echo "⚠️ TELEGRAM_BOT_TOKEN not set. Manual webhook setup required:"
        echo "   curl -X POST \"https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook\" \\"
        echo "        -H \"Content-Type: application/json\" \\"
        echo "        -d \"{\\\"url\\\": \\\"$FUNCTION_URL\\\"}\""
    fi
    
else
    echo "❌ Deployment failed!"
    exit 1
fi

echo "🎉 Telegram Bot deployment complete!"