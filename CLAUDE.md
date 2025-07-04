# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏗️ Current Architecture Overview

### Unified Messaging System (NEW - July 2025)
The system has transitioned from email-based communication to a **unified messaging platform** supporting:
- **Telegram** (Primary): Handles @username communication via bot
- **SMS**: Twilio and MessageCentral for phone number communication  
- **Email Processing**: Task detection and routing (no longer for responses)

### Core Components

#### 1. Task Processing Flow
```
Frontend/Email → Unified Task Processor → Messaging Channel → LangGraph Agent → Response
```

#### 2. Messaging Abstraction Layer
- **Location**: `messaging/` directory
- **Purpose**: Provider-agnostic messaging with easy swapping between Telegram/SMS
- **Components**:
  - `messaging/base.py` - Core interfaces and message manager
  - `messaging/telegram_provider.py` - Telegram Bot API integration
  - `messaging/twilio_provider.py` - Twilio SMS integration  
  - `messaging/messagecentral_provider.py` - MessageCentral SMS integration
  - `messaging/handler.py` - Unified message processing with LangGraph

#### 3. Cloud Functions (Active)
- **`email-watcher`** - Email processing with task detection and deletion
- **`telegram-function`** - Telegram webhook handler with user mapping
- **`unified-task-processor`** - Routes tasks to appropriate messaging channels
- **`send-email-simple`** - Utility for sending emails

## 📋 Development Commands

### Cloud Function Operations
```bash
# Deploy email watcher (detects task emails and deletes them)
cd email_watcher_function
npm run deploy

# Deploy Telegram function
cd telegram_function  
./deploy_telegram_function.sh

# Deploy unified task processor
cd unified_task_processor
./deploy_unified_task_processor.sh

# Check function logs
gcloud functions logs read email-watcher --region=us-central1 --limit=30
gcloud functions logs read telegram-function --region=us-central1 --limit=30
```

### Local Testing
```bash
# Test LangGraph SDK integration
python test_langgraph_sdk.py

# Test unified messaging locally
cd messaging
python -m pytest test_providers.py

# Run email watcher locally
cd email_watcher_function
node run_local.js
```

### Environment Setup
```bash
# Install messaging dependencies
pip install -r messaging/requirements.txt

# Install email function dependencies  
cd email_watcher_function
npm install
```

## 🔄 Message Routing Logic

### Phone Number Format Detection
- **Numeric phone** (e.g., `+1234567890`) → SMS via Twilio/MessageCentral
- **Non-numeric handle** (e.g., `@username`) → Telegram via bot

### Task Creation Sources
1. **Frontend Form** → `unified-task-processor` → Messaging channel
2. **Email** → `email-watcher` → Task detection → `unified-task-processor` → Messaging channel

### User Mapping (Telegram)
- **Username → Chat ID**: Stored in Firestore `telegram_users` collection
- **Auto-mapping**: When users first message the bot
- **Lookup**: Required for sending messages to @username handles

## 🗂️ Key Files and Purposes

### Unified Messaging System
- `messaging/base.py` - Core messaging abstractions and manager
- `messaging/telegram_provider.py` - Telegram Bot API implementation
- `messaging/twilio_provider.py` - Twilio SMS provider
- `messaging/messagecentral_provider.py` - MessageCentral SMS provider
- `messaging/handler.py` - Unified message processing with LangGraph integration

### Cloud Functions (Current)
- `email_watcher_function/index.js` - Email processing with task detection and deletion
- `telegram_function/main.py` - Telegram webhook with user mapping and pending task detection
- `unified_task_processor/main.py` - Task routing to appropriate messaging channels

### LangGraph Integration
- `oneNodeRemMem.py` - Main conversational agent
- `test_langgraph_sdk.py` - SDK integration testing
- `langgraph.json` - Deployment configuration

## 🔧 Environment Variables

### Required for All Functions
```bash
# LangGraph Integration
LANGGRAPH_DEPLOYMENT_URL=https://prizm2-9d0348d2abe5594d8b533da6f9b05cac.us.langgraph.app
LANGGRAPH_API_KEY=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

# Firebase Configuration
FIREBASE_PROJECT_ID=prizmpoc
FIREBASE_API_KEY=your-firebase-key
FIREBASE_AUTH_DOMAIN=your-domain.firebaseapp.com
FIREBASE_STORAGE_BUCKET=your-bucket.appspot.com

# Telegram Integration
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# SMS Integration  
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-number
MC_CUSTOMER_ID=your-messagecentral-id
MC_PASSWORD=your-messagecentral-password

# Email Processing
GMAIL_USER=foilboi808@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
UNIFIED_TASK_PROCESSOR_URL=https://unified-task-processor-cs64iuly6q-uc.a.run.app
```

## 📊 Data Storage

### Firestore Collections
- **`telegram_users`** - Username to chat_id mappings
- **`tasks`** - Task records with messaging channel info
- **`processedEmails`** - Email deduplication tracking

### Task Record Schema
```json
{
  "task_id": "unique_task_identifier",
  "customer_email": "user@example.com", 
  "phone_number": "+1234567890 or @username",
  "messaging_provider": "telegram|twilio|messagecentral",
  "contact_identifier": "chat_id or phone_number",
  "conversation_state": {
    "turn_count": 0,
    "is_complete": false,
    "conversation_history": ""
  }
}
```

## 🚀 Current Features

### ✅ Implemented
- Unified messaging abstraction with provider swapping
- Telegram bot integration with username mapping
- SMS integration (Twilio + MessageCentral)
- Email task detection and automatic deletion
- Task routing based on phone number format
- LangGraph agent integration
- Firestore state management

### 🔄 Active Flows
1. **New Task Flow**: Frontend/Email → Task Processor → Messaging → LangGraph → Response
2. **Message Flow**: User Message → Provider → Unified Handler → LangGraph → Response
3. **Email Cleanup**: Task emails automatically deleted after processing

## 🔍 Troubleshooting

### Check Function Status
```bash
gcloud functions list --filter="name~(email|telegram|unified)"
```

### View Recent Logs
```bash
gcloud functions logs read FUNCTION_NAME --region=us-central1 --limit=20
```

### Test Deployments
```bash
gcloud functions call FUNCTION_NAME --region=us-central1
```

### Common Issues
- **Telegram messages fail**: Check username to chat_id mapping in Firestore
- **SMS routing fails**: Verify phone number format detection
- **Task creation fails**: Check unified task processor logs and environment variables
- **Email deletion fails**: Verify IMAP permissions and UID availability