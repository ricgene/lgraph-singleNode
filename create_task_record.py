import os
from google.cloud import firestore
from datetime import datetime
import uuid

# Initialize Firestore client
db = firestore.Client()

def create_task_record(user_email, task_title, task_description, task_type="home_improvement"):
    """
    Create a task record with the key structure: userEmail,taskTitle,timestamp
    """
    # Generate a unique timestamp-based ID
    timestamp = datetime.now().isoformat()
    task_id = f"{user_email}_{task_title}_{timestamp}"
    
    # Create the task document
    task_data = {
        "taskId": task_id,
        "userEmail": user_email,
        "taskTitle": task_title,
        "taskDescription": task_description,
        "taskType": task_type,
        "createdAt": timestamp,
        "status": "active",
        "agentStateKey": f"taskAgent1_{user_email}_{task_title}_{timestamp}",
        "metadata": {
            "version": "1.0",
            "createdBy": "system",
            "lastUpdated": timestamp
        }
    }
    
    # Add to tasks collection
    task_ref = db.collection('tasks').document(task_id)
    task_ref.set(task_data)
    
    print(f"✅ Created task record: {task_id}")
    print(f"📋 Task Title: {task_title}")
    print(f"👤 User: {user_email}")
    print(f"🔗 Agent State Key: {task_data['agentStateKey']}")
    
    return task_id, task_data['agentStateKey']

def update_agent_state_link(user_email, task_title, agent_state_key):
    """
    Update the agent state to reference the task record
    """
    # Get the current agent state
    agent_ref = db.collection('taskAgent1').document(user_email)
    agent_doc = agent_ref.get()
    
    if agent_doc.exists:
        current_data = agent_doc.to_dict()
        
        # Add task reference
        current_data['currentTask'] = {
            "taskId": f"{user_email}_{task_title}_{datetime.now().isoformat()}",
            "taskTitle": task_title,
            "agentStateKey": agent_state_key,
            "linkedAt": datetime.now().isoformat()
        }
        
        # Update the document
        agent_ref.set(current_data, merge=True)
        print(f"✅ Updated agent state for {user_email} with task reference")
    else:
        print(f"⚠️ No existing agent state found for {user_email}")

if __name__ == "__main__":
    # Example usage
    user_email = "richard.genet@gmail.com"
    task_title = "Home Kitchen Renovation"
    task_description = "Complete kitchen renovation including new cabinets, countertops, and appliances"
    
    print("🏗️ Creating task record with new key structure...")
    task_id, agent_state_key = create_task_record(user_email, task_title, task_description)
    
    print("\n🔗 Linking agent state to task...")
    update_agent_state_link(user_email, task_title, agent_state_key)
    
    print(f"\n✅ Task setup complete!")
    print(f"📝 Task ID: {task_id}")
    print(f"🤖 Agent State Key: {agent_state_key}") 