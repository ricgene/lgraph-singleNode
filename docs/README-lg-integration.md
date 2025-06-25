# LangGraph Integration Documentation

## Overview

This document tracks the conversation flow between the user and the LangGraph agent (`oneNodeRemMem.py`) through multiple turns, showing the exact input/output structures at each step.

## Agent Details

- **Agent File**: `oneNodeRemMem.py`
- **Agent Name**: Helen (Prizm Real Estate Concierge Service)
- **Purpose**: Collect information about home tasks and guide users through the process
- **Max Turns**: 7 turns maximum
- **Completion States**: `TASK_PROGRESSING`, `TASK_ESCALATION`, `OTHER`

## Input/Output Structure

### Input Structure (to agent)
```json
{
  "user_input": "User's response to agent's question",
  "previous_state": {
    "conversation_history": "Previous conversation text...",
    "all_info_collected": false,
    "user_email": "user@example.com"
  }
}
```

### Output Structure (from agent)
```json
{
  "question": "Agent's next question or empty if complete",
  "conversation_history": "Full conversation history with Q&A",
  "is_complete": true/false,
  "completion_state": "TASK_PROGRESSING|TASK_ESCALATION|OTHER",
  "user_email": "user@example.com"
}
```

## Conversation Flow Examples

### Example 1: Basic Task Discussion

#### Turn 1 (Initial)
**Input:**
```json
{
  "user_input": "",
  "previous_state": null,
  "user_email": "test@example.com"
}
```

**Output:**
```json
{
  "question": "Great! Are you ready to discuss the details of your home task now?",
  "conversation_history": "\nQuestion: Great! Are you ready to discuss the details of your home task now?\nLearned: The customer is ready to discuss their home task.",
  "is_complete": false,
  "completion_state": "OTHER",
  "user_email": "test@example.com"
}
```

#### Turn 2
**Input:**
```json
{
  "user_input": "Yes, I am ready to discuss my task",
  "previous_state": {
    "conversation_history": "\nQuestion: Great! Are you ready to discuss the details of your home task now?\nLearned: The customer is ready to discuss their home task.",
    "all_info_collected": false,
    "user_email": "test@example.com"
  }
}
```

**Output:**
```json
{
  "question": "That's great! Will you be reaching out to the contractor for your home task?",
  "conversation_history": "\nQuestion: Great! Are you ready to discuss the details of your home task now?\nLearned: The customer is ready to discuss their home task.\nQuestion: That's great! Will you be reaching out to the contractor for your home task?\nLearned: The customer is ready to discuss their home task and will reach out to the contractor.",
  "is_complete": false,
  "completion_state": "OTHER",
  "user_email": "test@example.com"
}
```

#### Turn 3
**Input:**
```json
{
  "user_input": "Yes, I will reach out to the contractor",
  "previous_state": {
    "conversation_history": "\nQuestion: Great! Are you ready to discuss the details of your home task now?\nLearned: The customer is ready to discuss their home task.\nQuestion: That's great! Will you be reaching out to the contractor for your home task?\nLearned: The customer is ready to discuss their home task and will reach out to the contractor.",
    "all_info_collected": false,
    "user_email": "test@example.com"
  }
}
```

**Output:**
```json
{
  "question": "Do you have any concerns or questions about your home task that you would like to discuss?",
  "conversation_history": "\nQuestion: Great! Are you ready to discuss the details of your home task now?\nLearned: The customer is ready to discuss their home task.\nQuestion: That's great! Will you be reaching out to the contractor for your home task?\nLearned: The customer is ready to discuss their home task and will reach out to the contractor.\nQuestion: Do you have any concerns or questions about your home task that you would like to discuss?\nLearned: The customer will reach out to the contractor for their home task.",
  "is_complete": false,
  "completion_state": "OTHER",
  "user_email": "test@example.com"
}
```

## Information Collection Goals

The agent collects 3 key pieces of information:

1. **Are they ready to discuss their Task?**
2. **Will they reach out to the contractor <C>?**
3. **Do they have any concerns or questions?**

## Completion Logic

- **TASK_PROGRESSING**: User will move forward with the task
- **TASK_ESCALATION**: User needs additional assistance or has concerns
- **OTHER**: Conversation still in progress

## Conversation History Format

The conversation history follows this pattern:
```
Question: [Agent's question]
Learned: [What the agent learned from the response]
Question: [Next agent question]
Learned: [Updated learning]
...
```

## Testing

Use the interactive test script:
```bash
python tests/lg-local-hil-test.py
```

This will show detailed input/output for each turn in real-time.

---

*This document will be updated as we test more conversation examples.* 