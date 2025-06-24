# Email-Based Conversational Agent System

This project implements an intelligent email-based conversational agent using Google Cloud Functions, LangGraph, and Firebase. The system automatically processes incoming emails, conducts progressive questioning, and sends follow-up responses via email.

## 🏗️ System Architecture

The system consists of three main Cloud Functions working together:

```
Cloud Scheduler → email-watcher → Pub/Sub → process-incoming-email → send-email-simple → Gmail SMTP
```

### Components

1. **`email-watcher`** - Node.js Cloud Function that polls Gmail IMAP for new emails
2. **`process-incoming-email`** - Python Cloud Function that processes emails via Pub/Sub
3. **`send-email-simple`** - Python Cloud Function that sends response emails via SMTP
4. **Cloud Scheduler** - Triggers email watcher every 2 minutes
5. **Firebase Firestore** - Stores conversation state and distributed locks

## 🚀 Quick Start

### Prerequisites

- Google Cloud Project with billing enabled
- Gmail account with App Password
- OpenAI API key
- Firebase project

### 1. Environment Setup

Create a `.env` file with your credentials:

```bash
# Gmail Configuration
GMAIL_USER=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-openai-key

# Firebase Configuration (optional, for advanced features)
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef
```

### 2. Deploy the System

Follow the complete deployment guide: **[EMAIL_FUNCTION_DEPLOYMENT.md](EMAIL_FUNCTION_DEPLOYMENT.md)**

The deployment process includes:
- Setting up Google Cloud APIs
- Deploying all three Cloud Functions
- Creating Pub/Sub topics
- Configuring Cloud Scheduler
- Testing the complete system

### 3. Test the System

Send an email to your Gmail account with subject "Re: Prizm Task Question" and the system will:
1. Detect the email via IMAP polling
2. Process it through the LangGraph agent
3. Send a follow-up question via email
4. Continue the conversation for up to 7 turns

## 📁 Project Structure

```
lgraph-singleNode-25May16/
├── email_watcher_function/          # email-watcher Cloud Function
│   ├── index.js                     # Main function code
│   └── package.json                 # Node.js dependencies
├── cloud_function/                  # process-incoming-email Cloud Function
│   ├── main.py                      # Main function code
│   ├── agent.py                     # LangGraph agent logic
│   └── requirements.txt             # Python dependencies
├── simple_email_function/           # send-email-simple Cloud Function
│   ├── main.py                      # Main function code
│   └── requirements.txt             # Python dependencies
├── email_watcher_minimal.js         # Local development version
├── EMAIL_FUNCTION_DEPLOYMENT.md     # Complete deployment guide
├── architecture.mmd                 # System architecture diagram
└── README.md                        # This file
```

## 🔧 Features

### Core Functionality
- **Automatic Email Processing** - Monitors Gmail for new emails every 2 minutes
- **Progressive Questioning** - Conducts structured conversations with up to 7 questions
- **State Management** - Maintains conversation state in Firebase Firestore
- **Distributed Locking** - Prevents race conditions with multiple instances
- **Duplicate Prevention** - Avoids processing the same email multiple times

### Technical Features
- **Cloud-Native** - Fully deployed on Google Cloud Functions
- **Scalable** - Automatically scales based on demand
- **Reliable** - Uses Pub/Sub for message queuing and retry logic
- **Secure** - Uses Gmail App Passwords and environment variables
- **Cost-Effective** - Pay only for actual usage

## 📊 Monitoring

### Cloud Function Logs
   ```bash
# View email watcher logs
gcloud functions logs read email-watcher --limit=10 --region=us-central1

# View processing function logs
gcloud functions logs read process-incoming-email --limit=10 --region=us-central1

# View email sending function logs
gcloud functions logs read send-email-simple --limit=10 --region=us-central1
```

### Cloud Scheduler Status
```bash
# Check scheduler job status
gcloud scheduler jobs describe email-watcher-job --location=us-central1
```

### Firebase Firestore
Monitor conversation states and locks in the Firebase console.

## 🛠️ Development

### Local Testing
For local development and testing, use the minimal email watcher:

```bash
# Start local email watcher
source .env && node email_watcher_minimal.js
```

### Function URLs
- **email-watcher**: `https://us-central1-prizmpoc.cloudfunctions.net/email-watcher`
- **send-email-simple**: `https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple`

## 🔍 Troubleshooting

### Common Issues

1. **403 Forbidden Errors**
   - Ensure Cloud Functions are deployed with `--allow-unauthenticated`
   - Check IAM permissions for the service account

2. **IMAP Connection Errors**
   - Verify Gmail App Password is correct
   - Check Gmail IMAP settings are enabled
   - Ensure "Less secure app access" is configured

3. **Email Not Sending**
   - Check SMTP credentials in `send-email-simple` function
   - Verify Gmail App Password has SMTP permissions
   - Check function logs for specific error messages

4. **Duplicate Processing**
   - Verify only one Cloud Scheduler job is running
   - Check Firestore for proper lock management
   - Review function logs for lock acquisition issues

### Debug Commands
```bash
# Test email sending function
curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple \
  -H "Content-Type: application/json" \
  -d '{"to": "test@example.com", "subject": "Test", "body": "Test message"}'

# Test email watcher function
curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/email-watcher \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 📚 Documentation

- **[EMAIL_FUNCTION_DEPLOYMENT.md](EMAIL_FUNCTION_DEPLOYMENT.md)** - Complete deployment guide
- **[architecture.mmd](architecture.mmd)** - System architecture diagram
- **[architecture_detailed.mmd](architecture_detailed.mmd)** - Detailed component relationships
- **[email_processing_flow.mmd](email_processing_flow.mmd)** - Email processing sequence diagram

## 🔗 References

- [Google Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Firebase Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Gmail API Documentation](https://developers.google.com/gmail/api)

## 📄 License

This project is for educational and demonstration purposes.

---

**Last Updated**: June 2025  
**Status**: ✅ Production Ready - Fully deployed on Google Cloud Functions
