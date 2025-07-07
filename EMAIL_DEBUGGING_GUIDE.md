# Email Task Processing Debugging Guide

## 🎯 **Problem Solved: Email Parsing Issue**

### **Root Cause**
The email watcher function was incorrectly parsing email content that contained structured task data in the format:
```
"custemail":richard.genet@gmail.com,
"phone":@PoorRichard808,
"Task": t449,
"Category": Bathrooms/Showers,
```

But the original regex patterns were extracting malformed values like `": t449"` instead of `"t449"`, causing the unified task processor to receive invalid data and return 400 errors.

### **Solution Applied**
✅ **Fixed email parsing** in `email_watcher_function/index.js`
✅ **Deployed updated function** with improved parsing logic
✅ **Verified fix works** with test data
✅ **Confirmed Firestore task creation** is working correctly

## 🔥 **Firestore Task Creation - CONFIRMED WORKING**

The workflow **DOES** create tasks in Firestore. Here's what happens:

### **Task Record Structure**
When a task is processed, a record is created in the `tasks` collection with:
- **Document ID**: `{email}_{task_title}_{timestamp}` (e.g., `richard.genet_at_gmail.com_t449_2025-07-07T22:34:31.200974`)
- **Collection**: `tasks`
- **Fields**: customer info, task details, conversation state, messaging provider

### **Firestore Collections Used**
- ✅ **`tasks`** - Task records created by unified task processor
- ✅ **`telegram_users`** - Username to chat_id mappings  
- ✅ **`processedEmails`** - Email deduplication tracking
- ✅ **`conversations`** - Legacy conversation data (still used by some functions)

### **Verification**
```bash
# Test task creation
python3 test_task_creation.py

# Check Firestore manually
# Go to: https://console.firebase.google.com/project/prizmpoc/firestore
# Look for 'tasks' collection
```

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
- ✅ `Created task record [task_id] for [provider] channel`
- ✅ `Task created and conversation initiated`
- ❌ `400 Client Error: Bad Request` (indicates parsing issue)
- ❌ `Failed to send initial message`

### 3. **Test Email Parsing Locally**
```bash
# Test with your actual email content
node test_email_parsing_v2.js
```

### 4. **Test Task Creation**
```bash
# Test that Firestore records are created
python3 test_task_creation.py
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
6. create_task_record() creates Firestore record in 'tasks' collection
   ↓
7. Task processor routes to Telegram/SMS based on phone format
   ↓
8. LangGraph agent initiates conversation
   ↓
9. Email marked as processed and deleted
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

### **Issue: Task not appearing in Firestore**
**Cause:** Task creation failed or wrong collection
**Solution:**
- Check unified task processor logs for "Created task record"
- Verify looking in `tasks` collection (not `conversations`)
- Test with `python3 test_task_creation.py`

## 🧪 **Testing Commands**

### **Test Email Parsing**
```bash
node test_email_parsing_v2.js
```

### **Test Task Creation**
```bash
python3 test_task_creation.py
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
5. **Verify Firestore task record** is created in `tasks` collection

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
**Firestore:** ✅ **CONFIRMED** - Tasks are being created in the `tasks` collection. 