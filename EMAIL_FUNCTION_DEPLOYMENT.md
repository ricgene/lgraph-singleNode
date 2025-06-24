# Email Processing System - Deployment Guide

This guide covers the complete deployment, testing, and scheduling of the email-based conversational agent system using Google Cloud Functions.

## 🏗️ System Architecture

The system consists of three main components:

1. **`email-watcher`** - Node.js Cloud Function that polls Gmail IMAP for new emails
2. **`process-incoming-email`** - Python Cloud Function that processes emails via Pub/Sub
3. **`send-email-simple`** - Python Cloud Function that sends response emails via SMTP

```
Cloud Scheduler → email-watcher → Pub/Sub → process-incoming-email → send-email-simple → Gmail SMTP
```

## 📋 Prerequisites

### 1. Google Cloud Project Setup
```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable firestore.googleapis.com
```

### 2. Environment Variables
Create a `.env` file in the root directory:
```bash
# Gmail Configuration
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-openai-key

# Firebase Configuration (if using Firestore)
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
```

### 3. Gmail App Password Setup
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use this password in `GMAIL_APP_PASSWORD`

## 🚀 Deployment Steps

### Step 1: Deploy Email Watcher Function

```bash
# Navigate to email watcher function directory
cd email_watcher_function

# Install dependencies
npm install

# Deploy the function
source ../.env && gcloud functions deploy email-watcher \
  --gen2 \
  --runtime=nodejs20 \
  --region=us-central1 \
  --source=. \
  --entry-point=emailWatcher \
  --trigger-http \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars GMAIL_USER=$GMAIL_USER,GMAIL_APP_PASSWORD=$GMAIL_APP_PASSWORD \
  --allow-unauthenticated
```

### Step 2: Deploy Email Sending Function

```bash
# Navigate to simple email function directory
cd ../simple_email_function

# Deploy the function
source ../.env && gcloud functions deploy send-email-simple \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=send_email_simple \
  --trigger-http \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars GMAIL_USER=$GMAIL_USER,GMAIL_APP_PASSWORD=$GMAIL_APP_PASSWORD \
  --allow-unauthenticated
```

### Step 3: Deploy Email Processing Function

```bash
# Navigate to cloud function directory
cd ../cloud_function

# Deploy the function
source ../.env && gcloud functions deploy process-incoming-email \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=process_email_pubsub \
  --trigger-topic=incoming-messages \
  --memory=512MB \
  --timeout=540s \
  --set-env-vars EMAIL_FUNCTION_URL=https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/send-email-simple,OPENAI_API_KEY=$OPENAI_API_KEY
```

### Step 4: Create Pub/Sub Topic

```bash
# Create the Pub/Sub topic (if it doesn't exist)
gcloud pubsub topics create incoming-messages
```

### Step 5: Set Up Cloud Scheduler

```bash
# Create a scheduler job to trigger email watcher every 2 minutes
gcloud scheduler jobs create http email-watcher-job \
  --schedule="*/2 * * * *" \
  --uri="https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/email-watcher" \
  --http-method=POST \
  --location=us-central1 \
  --description="Check for new emails every 2 minutes"
```

## 🧪 Testing

### 1. Test Email Watcher Function

```bash
# Test the email watcher function directly
curl -X POST https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/email-watcher \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 2. Test Email Sending Function

```bash
# Test sending an email
curl -X POST https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/send-email-simple \
  -H "Content-Type: application/json" \
  -d '{
    "to": "test@example.com",
    "subject": "Test Email",
    "body": "This is a test email from the deployed function."
  }'
```

### 3. Test Complete Flow

1. Send an email to your monitored Gmail account
2. Wait for the Cloud Scheduler to trigger (up to 2 minutes)
3. Check the logs to see the processing flow

### 4. Monitor Logs

```bash
# View email watcher logs
gcloud functions logs read email-watcher --limit=20 --region=us-central1

# View processing function logs
gcloud functions logs read process-incoming-email --limit=20 --region=us-central1

# View email sending function logs
gcloud functions logs read send-email-simple --limit=20 --region=us-central1
```

## 📊 Monitoring and Management

### View Deployed Functions

```bash
# List all deployed functions
gcloud functions list

# Get function details
gcloud functions describe email-watcher --region=us-central1
```

### Update Functions

```bash
# Update a function (same command as deploy, but with --update-labels if needed)
gcloud functions deploy email-watcher \
  --gen2 \
  --runtime=nodejs20 \
  --region=us-central1 \
  --source=. \
  --entry-point=emailWatcher \
  --trigger-http \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars GMAIL_USER=$GMAIL_USER,GMAIL_APP_PASSWORD=$GMAIL_APP_PASSWORD
```

### Manage Cloud Scheduler

```bash
# List scheduler jobs
gcloud scheduler jobs list --location=us-central1

# Pause a job
gcloud scheduler jobs pause email-watcher-job --location=us-central1

# Resume a job
gcloud scheduler jobs resume email-watcher-job --location=us-central1

# Delete a job
gcloud scheduler jobs delete email-watcher-job --location=us-central1
```

## 🔧 Configuration Options

### Email Watcher Configuration

The email watcher can be configured by modifying `email_watcher_function/index.js`:

- **Target Email**: Change the email filter in the `processEmail` function
- **Search Criteria**: Modify the IMAP search criteria in `checkEmails` function
- **Processing Logic**: Customize how emails are parsed and processed

### Processing Function Configuration

The processing function configuration is in `cloud_function/agent.py`:

- **Conversation Logic**: Modify the agent prompts and conversation flow
- **State Management**: Configure how conversation state is stored
- **Response Format**: Customize email response formatting

### Scheduling Configuration

Adjust the Cloud Scheduler frequency:

```bash
# Every minute
--schedule="* * * * *"

# Every 5 minutes
--schedule="*/5 * * * *"

# Every hour
--schedule="0 * * * *"
```

## 🚨 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Gmail app password is correct
   - Ensure 2FA is enabled on Gmail account

2. **Function Timeout**
   - Increase timeout in deployment command
   - Check for long-running operations

3. **IMAP Connection Issues**
   - Verify Gmail IMAP is enabled
   - Check firewall/proxy settings

4. **Pub/Sub Delivery Issues**
   - Verify topic exists: `gcloud pubsub topics list`
   - Check function permissions

### Debug Commands

```bash
# Test IMAP connection locally
node email_watcher_minimal.js

# Check function status
gcloud functions describe email-watcher --region=us-central1

# View recent logs with errors
gcloud functions logs read email-watcher --limit=50 --region=us-central1 | grep -i error

# Test Pub/Sub manually
gcloud pubsub topics publish incoming-messages --message='{"test": "message"}'
```

## 📈 Scaling Considerations

### Performance Optimization

- **Memory**: Increase memory allocation for complex processing
- **Timeout**: Adjust timeout based on processing requirements
- **Concurrency**: Monitor function execution times

### Cost Optimization

- **Scheduler Frequency**: Reduce polling frequency during low-usage periods
- **Function Resources**: Right-size memory and timeout settings
- **Log Retention**: Configure log retention policies

## 🔒 Security Best Practices

1. **Environment Variables**: Use Google Secret Manager for sensitive data
2. **IAM Permissions**: Follow principle of least privilege
3. **Network Security**: Use VPC connectors if needed
4. **Input Validation**: Validate all email inputs
5. **Rate Limiting**: Implement rate limiting for email sending

## 📞 Support

For issues or questions:
1. Check the logs first: `gcloud functions logs read`
2. Verify configuration in `.env` file
3. Test individual components
4. Review Google Cloud documentation

---

**Note**: Replace `YOUR_PROJECT_ID` with your actual Google Cloud project ID throughout this guide. 