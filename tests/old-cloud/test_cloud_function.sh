#!/bin/bash

set -e

echo "🧪 Testing deployed cloud function with Firebase authentication..."

# Generate Firebase custom token
echo "🔑 Generating Firebase custom token..."
CUSTOM_TOKEN=$(python generate_firebase_token.py | grep "Custom token:" | sed 's/Custom token: //')

if [ -z "$CUSTOM_TOKEN" ]; then
    echo "❌ Failed to generate Firebase custom token"
    exit 1
fi

echo "✅ Custom token generated successfully"

# Exchange custom token for ID token
echo "🔄 Exchanging custom token for ID token..."
ID_TOKEN=$(node exchange_token.js "$CUSTOM_TOKEN" | grep -E "^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$" | head -1)

if [ -z "$ID_TOKEN" ]; then
    echo "❌ Failed to exchange custom token for ID token"
    echo "Trying alternative extraction method..."
    # Alternative: get the token from the curl command output
    ID_TOKEN=$(node exchange_token.js "$CUSTOM_TOKEN" | grep "Authorization: Bearer" | sed 's/.*Bearer //' | sed 's/\.\.\..*//')
fi

if [ -z "$ID_TOKEN" ]; then
    echo "❌ Still failed to extract ID token"
    exit 1
fi

echo "✅ ID token obtained successfully"

# Test the cloud function
echo "📡 Testing cloud function..."
curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -d '{
    "userEmail": "test@example.com",
    "userResponse": "Yes, I am ready to discuss my task",
    "taskTitle": "Test Task"
  }'

echo ""
echo "✅ Test completed!"
echo ""
echo "📋 To check logs:"
echo "gcloud functions logs read process-incoming-email --limit=10 --region=us-central1" 