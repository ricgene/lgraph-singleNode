# Email Integration Testing Guide

This guide explains how to test the complete email integration system that combines LangGraph conversation agent with email functionality.

## System Overview

The email integration system consists of:
1. **LangGraph Server** (`langgraph_server.py`) - Flask server exposing LangGraph functions
2. **Email Integration** (`email_langgraph_integration.js`) - Node.js service that watches for email replies
3. **GCP Email Function** - Deployed Cloud Function for sending emails
4. **LangGraph Agent** (`oneNodeRemMem.py`) - Core conversation logic

## Prerequisites

### 1. Environment Setup

Ensure you have the following environment variables in your `.env` file:

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-proj-your-openai-key-here

# Gmail credentials for receiving emails
GMAIL_USER=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password

# Deployed GCP email function URL
EMAIL_FUNCTION_URL=https://your-deployed-function-url.a.run.app

# LangChain/LangSmith (optional)
LANGCHAIN_API_KEY=your-langsmith-key
LANGSMITH_API_KEY=your-langsmith-key

# Firebase Configuration (optional - for production)
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

### 2. Gmail App Password Setup

1. Go to your Google Account settings
2. Enable 2-factor authentication
3. Generate an App Password for "Mail"
4. Use this App Password in your `.env` file

### 3. Dependencies Installation

#### Python Dependencies
```bash
# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### Node.js Dependencies
```bash
# Install Node.js dependencies
npm install
```

## Testing the Email Integration

### Step 1: Start the LangGraph Server

In one terminal:
```bash
# Activate virtual environment
source venv/bin/activate

# Start the Flask server
python langgraph_server.py
```

Expected output:
```
Starting LangGraph Email Integration Server...
Server will be available at: http://localhost:8000
Endpoints:
  POST /process_message - Process user responses
  POST /start_conversation - Start new conversation
  GET /health - Health check
Press Ctrl+C to stop the server
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8000
```

### Step 2: Start the Email Watcher

In another terminal:
```bash
# Activate virtual environment (for environment variables)
source venv/bin/activate

# Start the email watcher
node email_langgraph_integration.js
```

Expected output:
```
Gmail User: your-gmail@gmail.com
App Password length: 16
Email Function URL: https://your-deployed-function-url.a.run.app
Starting LangGraph Email Integration...
Starting to watch for new Prizm email replies...
Email integration is running. Press Ctrl+C to stop.
IMAP search date: 21-Jun-2025
No new Prizm email replies
```

### Step 3: Test the Email Flow

#### Option A: Start a New Conversation

Send an email to your Gmail account with:
- **Subject**: `Re: Prizm Task Question`
- **From**: Any email address you want to test with
- **Body**: Any response (e.g., "I'm ready to discuss my task")

#### Option B: Reply to Existing Conversation

Reply to any existing Prizm email with:
- **Subject**: Keep the original subject line
- **Body**: Your response to the question

### Step 4: Monitor the Process

Watch both terminals for activity:

**LangGraph Server Terminal:**
```
INFO:werkzeug:127.0.0.1 - - [21/Jun/2025 17:18:25] "POST /process_message HTTP/1.1" 200 -
INFO:oneNodeRemMem:✅ Email sent successfully to user@example.com
```

**Email Watcher Terminal:**
```
Processing reply from: user@example.com
User response: yes, I am ready...
Email sent via GCP function: Prizm Task Question #2
Processed email reply for: user@example.com
```

## Expected Conversation Flow

1. **Initial Question**: "Are you ready to discuss your task?"
2. **User Response**: "Yes, I'm ready"
3. **Follow-up Question**: "Will you be reaching out to the contractor?"
4. **User Response**: "Yes, I will"
5. **Final Question**: "Do you have any concerns or questions?"
6. **Completion**: Conversation ends with appropriate outcome

## Troubleshooting

### Common Issues

#### 1. Flask Module Not Found
```bash
# Solution: Install Flask
pip install flask flask-cors
```

#### 2. IMAP Authentication Error
```
IMAP error: Error: No supported authentication method(s) available
```
**Solution**: 
- Check your Gmail App Password is correct
- Ensure 2-factor authentication is enabled
- Verify GMAIL_USER and GMAIL_APP_PASSWORD in `.env`

#### 3. Email Function URL Not Found
```
❌ EMAIL_FUNCTION_URL not found in environment variables
```
**Solution**: Add the deployed GCP email function URL to your `.env` file

#### 4. OpenAI API Key Issues
```