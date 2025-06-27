#!/usr/bin/env python3
"""
Demo script to show what gets stored in Firestore with each turn
"""

import json
from datetime import datetime

def demo_firestore_storage():
    """Demonstrate what gets stored in Firestore with each turn"""
    
    print("🔥 FIRESTORE STORAGE DEMO")
    print("=" * 60)
    print("This shows what gets stored in the 'conversations' collection")
    print("with each turn of the conversation.\n")
    
    # Simulate a conversation with 3 turns
    conversation_turns = [
        {
            "user_input": "",
            "user_first_name": "John",
            "task_name": "Kitchen Renovation",
            "agent_response": "Hello John, are you ready to discuss the Kitchen Renovation you need assistance with?"
        },
        {
            "user_input": "Yes, I'm ready to discuss my task",
            "user_first_name": "John", 
            "task_name": "Kitchen Renovation",
            "agent_response": "Great John! Will you reach out to the contractor for your Kitchen Renovation?"
        },
        {
            "user_input": "Yes, I'll reach out to the contractor",
            "user_first_name": "John",
            "task_name": "Kitchen Renovation", 
            "agent_response": "Perfect John! Do you have any concerns or questions about your Kitchen Renovation?"
        }
    ]
    
    # Document key (without taskAgent1_ prefix)
    document_key = "john@example.com_Kitchen Renovation_2024-01-15T10:30:45.123Z"
    
    # Initial document structure
    firestore_document = {
        "taskId": "john@example.com_Kitchen Renovation_2024-01-15T10:30:45.123Z",
        "taskTitle": "Kitchen Renovation",
        "userEmail": "john@example.com",
        "userFirstName": "John",
        "createdAt": "2024-01-15T10:30:45.123Z",
        "lastUpdated": "2024-01-15T10:30:45.123Z",
        "status": "active",
        "conversationHistory": [],
        "fullInputHistory": []
    }
    
    print(f"📄 Document Key: {document_key}")
    print(f"📁 Collection: conversations")
    print()
    
    # Simulate each turn
    for turn_num, turn in enumerate(conversation_turns, 1):
        print(f"🔄 TURN {turn_num}")
        print("-" * 40)
        
        # Update timestamps
        current_timestamp = datetime.now().isoformat()
        firestore_document["lastUpdated"] = current_timestamp
        
        # Add to conversation history
        firestore_document["conversationHistory"].append({
            "userMessage": turn["user_input"],
            "agentResponse": turn["agent_response"],
            "timestamp": current_timestamp
        })
        
        # Create the full input that was sent to the agent
        full_input = {
            "user_input": turn["user_input"],
            "user_first_name": turn["user_first_name"],
            "task_name": turn["task_name"],
            "previous_state": {
                "conversation_history": "\n".join([
                    f"Question: {h['agentResponse']}\nLearned: User said: {h['userMessage']}"
                    for h in firestore_document["conversationHistory"][:-1]  # All but current
                ]),
                "is_complete": False,
                "user_email": "john@example.com"
            }
        }
        
        # Add to full input history
        firestore_document["fullInputHistory"].append({
            "input": full_input,
            "timestamp": current_timestamp,
            "turn_number": turn_num
        })
        
        print(f"👤 User: '{turn['user_input']}'")
        print(f"🤖 Agent: '{turn['agent_response']}'")
        print(f"📊 Conversation History entries: {len(firestore_document['conversationHistory'])}")
        print(f"📋 Full Input History entries: {len(firestore_document['fullInputHistory'])}")
        print()
        
        # Show the full input for this turn
        print(f"📤 FULL INPUT TO AGENT (Turn {turn_num}):")
        print(json.dumps(full_input, indent=2))
        print()
        
        # Show what gets stored in Firestore
        print(f"💾 FIRESTORE UPDATE (Turn {turn_num}):")
        print(f"Collection: conversations")
        print(f"Document: {document_key}")
        print(f"Operation: set()")
        print(f"Data: {json.dumps(firestore_document, indent=2)}")
        print()
        print("=" * 60)
        print()
    
    # Final state
    print("🏁 FINAL FIRESTORE DOCUMENT:")
    print("=" * 60)
    print(json.dumps(firestore_document, indent=2))
    
    print("\n" + "=" * 60)
    print("📋 KEY FEATURES:")
    print("✅ No email processing or locking")
    print("✅ Simple key structure (no taskAgent1_ prefix)")
    print("✅ Full input history grows with each turn")
    print("✅ User first name and task name in every input")
    print("✅ Complete conversation context preserved")
    print("✅ Timestamps for audit trail")

if __name__ == "__main__":
    demo_firestore_storage() 