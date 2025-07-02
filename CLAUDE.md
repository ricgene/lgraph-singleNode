# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Environment
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start local LangGraph server
python langgraph_server.py

# Run specific tests
python test_live_conversation.py
python test_messagecentral_integration.py
python test_telegram_integration.py
```

### Node.js Environment
```bash
# Install Node.js dependencies
npm install

# Start local email integration
npm start

# Start email watcher locally
source .env && node email_langgraph_integration.js
```

### LangGraph Operations
```bash
# Deploy LangGraph service (requires langgraph CLI)
langgraph deploy

# Test LangGraph service locally
langgraph dev
```

### Cloud Function Deployment
```bash
# Deploy email processing function (Pub/Sub triggered)
./deploy_process_email.sh

# Deploy HTTP email processing function
./deploy_updated_cloud_function.sh
```

### Testing Commands
```bash
# Test Telegram bot integration
python test_telegram_integration.py

# Test HTTP webhook with full payload
curl -X POST https://process-message-http-cs64iuly6q-uc.a.run.app \
  -H "Content-Type: application/json" \
  -d '{"Customer Name": "Test User", "custemail": "test@example.com", "Task": "Test Task"}'

# Test Telegram webhook directly
curl -X POST http://localhost:5000/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": {"chat": {"id": 123}, "from": {"id": 123, "username": "test"}, "text": "Hello bot!"}}'

# Check Telegram bot health
curl http://localhost:5000/telegram/health
```

## Architecture Overview

### Core System Components
- **Telegram Integration** (Primary): Telegram webhooks → Flask server → LangGraph → Telegram responses
- **SMS Integration**: Twilio/MessageCentral webhooks → Cloud Functions → LangGraph → SMS Response  
- **LangGraph Agent**: Deployed on LangGraph Cloud, handles conversational AI with 7-turn limit
- **State Management**: Firebase Firestore for persistent conversation storage
- **Email Processing** (Deprecated): Gmail IMAP → Cloud Scheduler → Pub/Sub → Cloud Functions → LangGraph → Email Response

### Key Files and Their Purposes

#### LangGraph Implementation
- `oneNodeRemMem.py` - Main LangGraph conversation agent with configurable prompts (prizm/generic/debug modes)
- `langgraph.json` - LangGraph deployment configuration defining the "moBettah" graph
- `langgraph_server.py` - Local Flask server for testing LangGraph functionality

#### Cloud Functions  
- `cloud_function/main.py` - Primary cloud function with HTTP and Pub/Sub triggers for email processing
- `cloud_function/agent.py` - Agent orchestration logic that calls deployed LangGraph service
- `simple_email_function/main.py` - SMTP email sending via Gmail App Password

#### Email Integration
- `email_langgraph_integration.js` - Node.js email watcher using IMAP with Firebase state management
- `email_watcher_function/index.js` - Cloud Function version of email watcher

#### Communication Integrations
- `telegram_bot.py` - Primary Telegram Bot integration with Flask webhook server
- `messagecentral_sms.py` - MessageCentral SMS provider integration
- `sms_webhook_server.py` - Local webhook server for SMS testing
- `email_langgraph_integration.js` - Deprecated email integration

### Configuration and State Management

#### Environment Variables Required
```bash
# Telegram Configuration (Primary)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook

# OpenAI Configuration  
OPENAI_API_KEY=your-openai-key

# LangGraph Deployment
LANGGRAPH_DEPLOYMENT_URL=your-langgraph-url
LANGGRAPH_API_KEY=your-langgraph-key

# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_API_KEY=your-firebase-key

# SMS Configuration
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
USE_MESSAGECENTRAL=true/false

# Email Configuration (Deprecated)
GMAIL_USER=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
```

#### State Structure
Conversation states stored in Firestore with schema:
```json
{
  "conversation_history": "Question: ...\nLearned: ...",
  "is_complete": false,
  "turn_count": 3,
  "user_email": "user@example.com", 
  "completion_state": "in_progress"
}
```

### Communication Flow Patterns
1. **Email Flow**: IMAP polling → Pub/Sub message → Firebase auth → LangGraph processing → SMTP response
2. **SMS Flow**: Webhook → Authentication → LangGraph processing → SMS API response
3. **State Management**: All conversations tracked with unique keys: `{user_email}_{task_title}_{timestamp}`

### Agent Behavior
- **Turn Limit**: Maximum 7 conversation turns per task
- **Prompt Modes**: Configurable via `AGENT_PROMPT_TYPE` (prizm/generic/debug)
- **Task Completion**: Automatically determined by LangGraph agent based on information gathering
- **Memory**: Full conversation history maintained in Firestore

### Deployment Architecture
- **Google Cloud Functions**: Serverless email/SMS processing
- **LangGraph Cloud**: AI agent hosting with SDK integration
- **Firebase Firestore**: Persistent state and authentication  
- **Cloud Scheduler**: Automated email polling every 2 minutes
- **Pub/Sub**: Asynchronous message processing between components

### Testing Approach
- Local testing via Flask server (`langgraph_server.py`)
- Live integration tests for SMS providers (`test_messagecentral_integration.py`)
- End-to-end conversation testing (`test_live_conversation.py`)
- Cloud function testing via HTTP endpoints and deployment scripts