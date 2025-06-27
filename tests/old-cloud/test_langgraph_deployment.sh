#!/bin/bash

# Test script for deployed LangGraph service
echo "🧪 Testing deployed oneNodeRemMem service..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one with:"
    echo "   LANGGRAPH_DEPLOYMENT_URL=your-deployment-url"
    echo "   LANGGRAPH_API_KEY=your-api-key"
    exit 1
fi

# Run the test
python test_deployed_langgraph.py

echo ""
echo "✅ Test completed!" 