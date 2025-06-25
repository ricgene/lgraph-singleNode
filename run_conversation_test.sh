#!/bin/bash

# Run the LangGraph conversation test
# This script will start the test and capture all input/output to a log file

echo "🚀 Starting LangGraph Conversation Test"
echo "======================================"

# Check if Python script exists
if [ ! -f "tests/lg-local-hil-test.py" ]; then
    echo "❌ Error: tests/lg-local-hil-test.py not found"
    exit 1
fi

# Make sure the script is executable
chmod +x tests/lg-local-hil-test.py

# Run the test
echo "📝 Running test... (all input/output will be logged to conversation_log_*.json)"
echo ""

python3 tests/lg-local-hil-test.py

echo ""
echo "✅ Test completed!"
echo "📊 Check the generated conversation_log_*.json file for complete input/output stream" 