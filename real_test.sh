#!/bin/bash

echo "🧪 Real test of deployed cloud function with Firebase authentication..."

# Use the ID token we already generated from manual testing
ID_TOKEN="eyJhbGciOiJSUzI1NiIsImtpZCI6IjNiZjA1MzkxMzk2OTEzYTc4ZWM4MGY0MjcwMzM4NjM2NDA2MTBhZGMiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vcHJpem1wb2MiLCJhdWQiOiJwcml6bXBvYyIsImF1dGhfdGltZSI6MTc1MDg5MjM2OCwidXNlcl9pZCI6InRlc3Qtc2VydmljZS1hY2NvdW50LXVzZXIiLCJzdWIiOiJ0ZXN0LXNlcnZpY2UtYWNjb3VudC11c2VyIiwiaWF0IjoxNzUwODkyMzY4LCJleHAiOjE3NTA4OTU5NjgsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnt9LCJzaWduX2luX3Byb3ZpZGVyIjoiY3VzdG9tIn19.vrUZhd9R3TMIQPdnLGoYs5lYMvi4d85ioYuyxmLww21gbhfxh_cr1lx8LDSAGfCU7ZWFhkILwFVv7r1nF5-pWQrmG9xAqLngttXTHZRurgszo_97ltM5dAwa3c4bx-yvPD1rMD_L6YG8Uo_oYNJKSkmGMNA2oAT0cLZFYXpjvKYKrWH7nUuwHVRfQBwvOote0oJCxdfmwsTghM2J4xFKoaWRTwd9LPq6gcDMtFl8MQQQqMQSBNqJExVGEYzgxbbWAMOXkcdSHWz4GcKDLxXjw2yhb6y-m3AvPDi_gvIpNwzbFTarhKdsHdM97BOvGh2_xZ-QoJAlGU-RBZSzh2qtyQ"

echo "📡 Testing cloud function with real Firebase ID token..."
curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/process-incoming-email \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -d '{
    "userEmail": "test@example.com",
    "userResponse": "Yes, I am ready to discuss my task",
    "taskTitle": "Test Task"
  }'

echo ""
echo "✅ Real test completed!"
echo ""
echo "📋 To check logs:"
echo "gcloud functions logs read process-incoming-email --limit=10 --region=us-central1" 