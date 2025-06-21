# LangGraph Email Integration

This project integrates LangGraph conversation agents with email functionality, allowing users to have conversations via email with an AI agent.

## Architecture

```
User Email ↔ IMAP (Receive) ↔ Node.js ↔ HTTP API ↔ Python Flask ↔ LangGraph
                ↓
            GCP Function (Send) ↔ User Email
```

## Setup

### 1. Install Dependencies

**Python Dependencies:**
```bash
pip install -r requirements.txt
```

**Node.js Dependencies:**
```bash
npm install
```

### 2. Environment Variables

Create a `.env` file with:

```env
# Gmail Configuration
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# GCP Email Function
EMAIL_FUNCTION_URL=https://sendemail-cs64iuly6q-uc.a.run.app

# LangGraph Configuration
OPENAI_API_KEY=sk-proj-...
LANGCHAIN_API_KEY=lsv2_pt_...
LANGGRAPH_CLOUD_LICENSE_KEY=lsv2_pt_...
LANGSMITH_API_KEY=lsv2_pt_...
```

### 3. Deploy GCP Email Function

Follow the instructions in `../gcp-agent-email2user/readme-deploy.md` to deploy the email sending function.

## Running the Integration

### Option 1: Run Both Services (Recommended)

**Terminal 1 - Start the Python Flask server:**
```bash
python langgraph_server.py
```

**Terminal 2 - Start the Node.js email watcher:**
```bash
node email_langgraph_integration.js
```

### Option 2: Use npm scripts

**Terminal 1:**
```bash
npm run server
```

**Terminal 2:**
```bash
npm start
```

## How It Works

### 1. Email Reception
- Node.js connects to Gmail via IMAP
- Watches for emails with subject "Re: Prizm Task Question"
- Extracts user responses from email body

### 2. LangGraph Processing
- Sends user response to Python Flask server
- Flask server calls LangGraph `process_message()` function
- Returns next question or completion status

### 3. Email Sending
- Sends next question via deployed GCP function
- Uses Gmail app password authentication
- Formats emails with Prizm branding

## API Endpoints

### Flask Server (http://localhost:8000)

- `POST /process_message` - Process user responses
- `POST /start_conversation` - Start new conversation
- `GET /health` - Health check

### Example Usage

**Start a conversation:**
```bash
curl -X POST http://localhost:8000/start_conversation \
  -H "Content-Type: application/json" \
  -d '{"user_email": "user@example.com"}'
```

**Process a response:**
```bash
curl -X POST http://localhost:8000/process_message \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Yes, I am ready to discuss my task",
    "previous_state": {"conversation_history": "", "is_complete": false},
    "user_email": "user@example.com"
  }'
```

## Testing

### 1. Test Email Function
```bash
curl -X POST https://sendemail-cs64iuly6q-uc.a.run.app \
  -H "Content-Type: application/json" \
  -d '{"to":"test@example.com","subject":"Test","body":"Hello"}'
```

### 2. Test Flask Server
```bash
curl http://localhost:8000/health
```

### 3. Test Full Integration
1. Start both services
2. Send an email to your Gmail account with subject "Re: Prizm Task Question"
3. Check if you receive a response

## Troubleshooting

### Common Issues

1. **IMAP Connection Failed**
   - Ensure Gmail app password is correct
   - Check if 2FA is enabled on Gmail account

2. **Flask Server Won't Start**
   - Check if port 8000 is available
   - Ensure all Python dependencies are installed

3. **GCP Function Errors**
   - Verify the function URL is correct
   - Check GCP function logs

### Logs

- **Node.js logs**: Email reception and sending status
- **Flask logs**: LangGraph processing and API calls
- **GCP logs**: Email function execution

## Security Notes

- Gmail app passwords are more secure than OAuth2 for this use case
- All sensitive data should be in environment variables
- Consider rate limiting for production use
- Monitor email sending quotas

## Production Deployment

For production, consider:
- Running services as systemd services
- Using PM2 for Node.js process management
- Setting up proper logging and monitoring
- Implementing error recovery and retry logic
- Using a proper database for conversation state persistence 