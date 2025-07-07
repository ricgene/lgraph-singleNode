# Email Task Processing Debugging Guide

## 🎯 **Problem Solved: Email Parsing Issue**

### **Root Cause**
The email watcher function was incorrectly parsing email content that contained structured task data in the format:
```
"custemail":richard.genet@gmail.com,
"phone":@PoorRichard808,
"Task": t449,
"Category": Bathrooms/Showers,
...
```

The original regex patterns were extracting values like `": t449"` instead of `"t449"`, causing the unified task processor to receive malformed data and return 400 errors.

### **Solution Applied**
✅ **Fixed email parsing** in `email_watcher_function/index.js`
✅ **Deployed updated function** with improved parsing logic
✅ **Verified fix works** with test data

## 🔍 **Debugging Steps for Future Issues**

### 1. **Check Email Watcher Logs**
```bash
gcloud functions logs read email-watcher --region=us-central1 --limit=20
```

**Look for:**
- ✅ `📋 Detected task creation email`
- ✅ `✅ Extracted [field]: [value]` messages
- ✅ `📋 Final extracted task data`
- ❌ `❌ Error calling unified task processor`

### 2. **Check Unified Task Processor Logs**
```bash
gcloud functions logs read unified-task-processor --region=us-central1 --limit=10
```

**Look for:**
- ✅ `Task created and conversation initiated`
- ❌ `400 Client Error: Bad Request` (indicates parsing issue)
- ❌ `Failed to send initial message`

### 3. **Test Email Parsing Locally**
```bash
# Test with your actual email content
node test_email_parsing_v2.js
```

### 4. **Test Unified Task Processor**
```bash
# Test with correctly parsed data
python3 test_fixed_task_processing.py
```

## 📧 **Email Processing Flow**

```
1. Email arrives at Gmail
   ↓
2. Cloud Scheduler triggers email-watcher (every 2 minutes)
   ↓
3. Email watcher detects task creation email
   ↓
4. extractTaskDataFromEmail() parses structured data
   ↓
5. Unified task processor receives clean data
   ↓
6. Task processor routes to Telegram/SMS based on phone format
   ↓
7. LangGraph agent initiates conversation
   ↓
8. Email marked as processed and deleted
```

## 🛠️ **Common Issues & Solutions**

### **Issue: 400 Bad Request from Telegram API**
**Cause:** Invalid chat_id or user hasn't messaged bot first
**Solution:** 
- Check Firestore `telegram_users` collection
- Verify user has messaged bot at least once
- Use diagnostic tool: `python3 telegram_diagnostic.py`

### **Issue: Email not being processed**
**Cause:** Email format not recognized or already processed
**Solution:**
- Check email subject contains task keywords
- Verify email not already in Firestore `processedEmails`
- Check email watcher logs for detection

### **Issue: Wrong data extracted**
**Cause:** Email parsing logic needs adjustment
**Solution:**
- Update `extractTaskDataFromEmail()` function
- Test with `node test_email_parsing_v2.js`
- Redeploy email watcher function

## 🧪 **Testing Commands**

### **Test Email Parsing**
```bash
node test_email_parsing_v2.js
```

### **Test Task Processing**
```bash
python3 test_fixed_task_processing.py
```

### **Test Telegram Integration**
```bash
python3 telegram_diagnostic.py
```

### **Trigger Email Processing**
```bash
curl -X POST https://us-central1-prizmpoc.cloudfunctions.net/email-watcher
```

## 📊 **Monitoring Commands**

### **Check All Function Status**
```bash
gcloud functions list --filter="name~(email|telegram|unified)"
```

### **View Recent Logs**
```bash
# Email watcher
gcloud functions logs read email-watcher --region=us-central1 --limit=10

# Unified task processor  
gcloud functions logs read unified-task-processor --region=us-central1 --limit=10

# Telegram function
gcloud functions logs read telegram-function --region=us-central1 --limit=10
```

### **Check Firestore Data**
```bash
# Check processed emails
gcloud firestore collections list

# Check telegram users
gcloud firestore collections list
```

## 🚀 **Next Steps**

1. **Send a new task email** to test the complete flow
2. **Monitor logs** to ensure processing works end-to-end
3. **Verify Telegram message** is sent to the user
4. **Check LangGraph conversation** is initiated

## 📝 **Email Format Requirements**

For successful processing, task emails should contain:
- Subject with task keywords (e.g., "your new task")
- Structured data in format: `"field":value`
- Required fields: `custemail`, `phone`, `Task`, `Category`
- Optional fields: `DueDate`, `Posted`, `FullAddress`, `Task Budget`, `State`, `vendors`

## 🔧 **Environment Variables**

Ensure these are set in your cloud functions:
```bash
# Email Processing
GMAIL_USER=foilboi808@gmail.com
GMAIL_APP_PASSWORD=your-app-password
UNIFIED_TASK_PROCESSOR_URL=https://unified-task-processor-cs64iuly6q-uc.a.run.app

# Telegram Integration
TELEGRAM_BOT_TOKEN=your-bot-token

# LangGraph Integration
LANGGRAPH_DEPLOYMENT_URL=your-langgraph-url
LANGGRAPH_API_KEY=your-api-key
```

---

**Status:** ✅ **FIXED** - Email parsing issue resolved, task processing should now work correctly. 