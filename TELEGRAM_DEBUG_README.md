# Telegram Debug Guide

Quick reference for debugging Telegram API issues in the Prizm system.

## 🚨 Common Issues

### 400 Bad Request: "chat not found"
- **Cause**: User hasn't messaged the bot yet
- **Solution**: User must send `/start` to @Aloha116bot first

### 409 Conflict on getUpdates
- **Cause**: Webhook and polling conflict
- **Solution**: Delete webhook to use polling mode

### 403 Forbidden
- **Cause**: Bot not member of group/channel
- **Solution**: Add bot to group or make it admin

## 🔧 Debug Commands

### 1. Check Basic Configuration
```bash
# Verify bot token and connectivity
python telegram_debug_tool.py check
```

### 2. Check Webhook Status
```bash
# See if webhook is causing conflicts
python check_webhook_status.py
```

### 3. View Recent Bot Activity
```bash
# See recent messages and valid chat_ids
python telegram_debug_tool.py updates
```

### 4. Check Firestore User Mapping
```bash
# Check if user exists in database
python check_firestore_mapping.py
```

### 5. Test Specific Chat ID
```bash
# Test if a chat_id is valid and accessible
python telegram_debug_tool.py diagnose <chat_id>
```

### 6. Test Task Processing
```bash
# Test the full task creation flow
python test_task_processing.py

# Test direct Telegram send
python test_task_processing.py direct
```

## 📋 Quick Troubleshooting Flow

### For 400 "chat not found" errors:

1. **Check if user exists in Firestore:**
   ```bash
   python check_firestore_mapping.py
   ```

2. **If no mapping found:**
   - User needs to message @Aloha116bot first
   - Send `/start` or any message to the bot

3. **If mapping exists but still failing:**
   ```bash
   python telegram_debug_tool.py diagnose <chat_id>
   ```

### For webhook conflicts:

1. **Check webhook status:**
   ```bash
   python check_webhook_status.py
   ```

2. **Delete webhook if needed:**
   - Run the script and choose 'y' when prompted

3. **Test polling mode:**
   ```bash
   python telegram_debug_tool.py updates
   ```

## 🎯 Environment Setup

Make sure these environment variables are set:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export LANGGRAPH_DEPLOYMENT_URL="your_langgraph_url"
export LANGGRAPH_API_KEY="your_langgraph_key"
```

## 📱 Bot Information

- **Bot Username**: @Aloha116bot
- **Bot Name**: Alertbot
- **Webhook URL**: https://telegram-webhook-cs64iuly6q-uc.a.run.app
- **Task Processor**: https://unified-task-processor-cs64iuly6q-uc.a.run.app

## 🔍 Understanding Chat IDs

- **Positive numbers** (e.g., `7321828510`): Private chats
- **Negative numbers** (e.g., `-987654321`): Group chats  
- **Negative starting with -100** (e.g., `-1001234567890`): Channels

Chat IDs are **permanent** and never change for a user-bot combination.

## 🛠️ Testing Task Creation

Use this format for testing:
```json
{
  "custemail": "user@example.com",
  "phone": "@username",
  "Task": "Test Task",
  "description": "Test description",
  "Category": "Test Category"
}
```

## 📊 Monitoring

### Check Cloud Function Logs
```bash
# Unified task processor logs
gcloud functions logs read unified-task-processor --region=us-central1 --limit=20

# Telegram webhook logs  
gcloud functions logs read telegram-webhook --region=us-central1 --limit=20
```

### Check Firestore Collections
- `telegram_users`: Username to chat_id mappings
- `tasks`: Task records with conversation state

## 🚀 Quick Fixes

### If user can't receive messages:
1. User sends `/start` to @Aloha116bot
2. Check Firestore mapping: `python check_firestore_mapping.py`
3. Test chat_id: `python telegram_debug_tool.py diagnose <chat_id>`

### If webhook is broken:
1. Delete webhook: `python check_webhook_status.py`
2. Redeploy if needed: `./deploy_telegram_function.sh`

### If task creation fails:
1. Test direct send: `python test_task_processing.py direct`
2. Test full flow: `python test_task_processing.py`
3. Check logs: `gcloud functions logs read unified-task-processor --limit=10`

## 📞 Support

If issues persist:
1. Run all debug commands above
2. Check Cloud Function logs
3. Verify environment variables
4. Test with a known working user (like @PoorRichard808) 