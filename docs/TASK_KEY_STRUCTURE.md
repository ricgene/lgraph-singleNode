# Task Key Structure Documentation

## Overview

The system now uses a **task-specific key structure** to ensure proper isolation between different tasks and prevent cross-contamination of conversation states.

## Key Structure

### Task ID Format
```
{userEmail}_{taskTitle}_{timestamp}
```

**Example:**
```
richard.genet@gmail.com_Prizm Task Question_2024-01-15T10:30:45.123456Z
```

### Agent State Key Format
```
taskAgent1_{userEmail}_{taskTitle}_{timestamp}
```

**Example:**
```
taskAgent1_richard.genet@gmail.com_Prizm Task Question_2024-01-15T10:30:45.123456Z
```

## Benefits

### 1. **Task Isolation**
- Each task gets its own unique document in Firestore
- No risk of conversation history mixing between different tasks
- Proper separation of user contexts

### 2. **Concurrent Task Support**
- Multiple tasks can run simultaneously for the same user
- Each task maintains its own conversation state
- No interference between different task conversations

### 3. **Audit Trail**
- Complete history of all tasks with timestamps
- Easy to track task creation and completion
- Full conversation history preserved per task

## Implementation

### Python Version (`cloud_function/main.py`)
- ✅ Already uses task-specific keys
- Uses `create_or_get_task_record()` function
- Stores in `tasks` collection with task-specific agent state keys

### Node.js Version (`cloud_function/index.js`)
- ✅ Updated to use task-specific keys
- Uses `findExistingTask()` and `createNewTask()` functions
- Maintains backward compatibility with existing data

## Data Structure

### Task Document (in `tasks` collection)
```json
{
  "taskId": "user@example.com_Task Title_2024-01-15T10:30:45.123456Z",
  "userEmail": "user@example.com",
  "taskTitle": "Task Title",
  "taskDescription": "Task initiated via email conversation",
  "taskType": "home_improvement",
  "createdAt": "2024-01-15T10:30:45.123456Z",
  "status": "active",
  "agentStateKey": "taskAgent1_user@example.com_Task Title_2024-01-15T10:30:45.123456Z",
  "conversationHistory": [
    {
      "userMessage": "I need help finding a house",
      "agentResponse": "I'd be happy to help you find a house!",
      "turnNumber": 1,
      "isComplete": false,
      "timestamp": "2024-01-15T10:30:45.123456Z"
    }
  ],
  "lastUpdated": "2024-01-15T10:35:12.789012Z"
}
```

### Agent State Document (in `taskAgent1` collection)
```json
{
  "agentStateKey": "taskAgent1_user@example.com_Task Title_2024-01-15T10:30:45.123456Z",
  "currentTask": {
    "taskId": "user@example.com_Task Title_2024-01-15T10:30:45.123456Z",
    "taskTitle": "Task Title",
    "userEmail": "user@example.com",
    "createdAt": "2024-01-15T10:30:45.123456Z",
    "lastUpdated": "2024-01-15T10:35:12.789012Z",
    "status": "active",
    "emailLock": null,
    "lastMsgSent": {
      "subject": "Prizm Task Question",
      "body": "Hello! Helen from Prizm here...",
      "messageHash": "abc123...",
      "timestamp": "2024-01-15T10:35:12.789012Z"
    },
    "conversationHistory": [
      {
        "userMessage": "I need help finding a house",
        "agentResponse": "I'd be happy to help you find a house!",
        "turnNumber": 1,
        "isComplete": false,
        "timestamp": "2024-01-15T10:30:45.123456Z"
      }
    ]
  },
  "createdAt": "2024-01-15T10:30:45.123456Z",
  "lastUpdated": "2024-01-15T10:35:12.789012Z"
}
```

## Migration

### From Old Structure
The old structure used simple email-based keys:
- **Old Task Key**: `user@example.com`
- **Old Structure**: All tasks for a user in one document

### To New Structure
The new structure uses task-specific keys:
- **New Task Key**: `taskAgent1_user@example.com_Task Title_2024-01-15T10:30:45.123456Z`
- **New Structure**: Each task gets its own document

### Backward Compatibility
- The system can handle both old and new data structures
- Existing tasks continue to work
- New tasks use the improved structure

## Functions

### Task Discovery
- `findExistingTask(userEmail, taskTitle)` - Finds existing active task
- `createNewTask(userEmail, taskTitle)` - Creates new task with unique key

### Key Generation
- `createTaskKey(userEmail, taskTitle, timestamp)` - Creates agent state key
- `createTaskId(userEmail, taskTitle, timestamp)` - Creates task ID

### State Management
- `loadTaskAgentStateByKey(taskKey)` - Loads task-specific state
- `saveTaskAgentStateByKey(taskKey, state)` - Saves task-specific state

## Testing

To test the new structure:

1. **Create multiple tasks** for the same user
2. **Verify isolation** - conversations don't mix
3. **Check concurrent processing** - multiple tasks can run simultaneously
4. **Validate conversation history** - each task maintains its own history

## Deployment

The updated Node.js cloud function needs to be redeployed:

```bash
gcloud functions deploy process-incoming-email --gen2 --runtime=python311 --region=us-central1 --source=cloud_function --entry-point=process_email_pubsub --trigger-topic=incoming-messages --memory=512MB --timeout=540s --set-env-vars EMAIL_FUNCTION_URL=https://us-central1-prizmpoc.cloudfunctions.net/send-email-simple,LANGGRAPH_SERVER_URL=https://prizm2-9d0348d2abe5594d8b533da6f9b05cac.us.langgraph.app,OPENAI_API_KEY=your-key-here
``` 