#!/bin/bash

# Deploy Unified Task Processor Cloud Function
# Routes tasks to appropriate messaging channels

set -e

echo "🚀 Deploying Unified Task Processor Cloud Function..."

# Configuration
FUNCTION_NAME="unified-task-processor"
REGION="us-central1"
SOURCE_DIR="unified_task_processor"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory $SOURCE_DIR not found"
    exit 1
fi

# Deploy the Cloud Function
echo "📦 Deploying function from $SOURCE_DIR..."

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=$SOURCE_DIR \
    --entry-point=process_task \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},LANGGRAPH_DEPLOYMENT_URL=${LANGGRAPH_DEPLOYMENT_URL},LANGGRAPH_API_KEY=${LANGGRAPH_API_KEY},TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID},TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN},TWILIO_PHONE_NUMBER=${TWILIO_PHONE_NUMBER},MC_CUSTOMER_ID=${MC_CUSTOMER_ID},MC_PASSWORD=${MC_PASSWORD},MC_PASSWORD_BASE64=${MC_PASSWORD_BASE64}" \
    --timeout=60s \
    --memory=512MB

if [ $? -eq 0 ]; then
    echo "✅ Unified Task Processor function deployed successfully!"
    
    # Get the function URL
    FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(serviceConfig.uri)")
    echo "📡 Function URL: $FUNCTION_URL"
    
    echo ""
    echo "🧪 Test with Telegram handle (non-numeric phone):"
    echo "curl -X POST \"$FUNCTION_URL\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{"
    echo "    \"Customer Name\": \"Test User\","
    echo "    \"custemail\": \"test@example.com\","
    echo "    \"phone_number\": \"@YourTelegramHandle\","
    echo "    \"Task\": \"Test Task\","
    echo "    \"description\": \"Testing Telegram integration\""
    echo "  }'"
    echo ""
    echo "🧪 Test with SMS phone (numeric phone):"
    echo "curl -X POST \"$FUNCTION_URL\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{"
    echo "    \"Customer Name\": \"Test User\","
    echo "    \"custemail\": \"test@example.com\","
    echo "    \"phone_number\": \"+1234567890\","
    echo "    \"Task\": \"Test Task\","
    echo "    \"description\": \"Testing SMS integration\""
    echo "  }'"
    
else
    echo "❌ Deployment failed!"
    exit 1
fi

echo "🎉 Unified Task Processor deployment complete!"