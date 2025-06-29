#!/usr/bin/env python3
"""
Local Agent-Firestore Loop Test System
Tests the agent conversation loop locally with configurable LLM backends
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
AGENT_PROMPT_TYPE = os.getenv("AGENT_PROMPT_TYPE", "debug")  # debug, prizm, generic
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
USE_MOCK_FIRESTORE = os.getenv("USE_MOCK_FIRESTORE", "true").lower() == "true"

logger.info(f"🚀 Starting local agent test - TEST_MODE: {TEST_MODE}")
logger.info(f"🤖 Agent prompt type: {AGENT_PROMPT_TYPE}")
logger.info(f"🔮 Mock LLM: {USE_MOCK_LLM}")
logger.info(f"🔥 Mock Firestore: {USE_MOCK_FIRESTORE}")

# Mock LLM implementation for fast local testing
class MockLLM:
    def __init__(self):
        self.call_count = 0
        
    def invoke(self, messages, config=None):
        self.call_count += 1
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # Simple mock responses based on input
        if self.call_count == 1 or not user_message:
            response = "Question: Hi! Are you ready to discuss your task?\nLearned: Starting conversation"
        elif "yes" in user_message.lower() and "ready" in user_message.lower():
            response = "Question: Great! Will you reach out to the contractor?\nLearned: User is ready to discuss the task"
        elif "yes" in user_message.lower() and "reach" in user_message.lower():
            response = "Question: Perfect! Do you have any concerns or questions?\nLearned: User will reach out to contractor"
        elif self.call_count >= 3:
            response = "Question: Thank you for your responses!\nLearned: User provided all needed info\nTASK_PROGRESSING"
        else:
            response = f"Question: Can you tell me more about that?\nLearned: User said: {user_message}"
        
        # Mock response object
        class MockResponse:
            def __init__(self, content):
                self.content = content
        
        logger.info(f"🔮 Mock LLM response (call #{self.call_count}): {response[:50]}...")
        return MockResponse(response)

# Mock Firestore implementation for local testing
class MockFirestore:
    def __init__(self):
        self.data = {}
        
    def collection(self, name):
        return MockCollection(name, self)
        
class MockCollection:
    def __init__(self, name, firestore):
        self.name = name
        self.firestore = firestore
        
    def document(self, doc_id):
        return MockDocument(doc_id, self.name, self.firestore)
        
    def stream(self):
        collection_data = self.firestore.data.get(self.name, {})
        docs = []
        for doc_id, data in collection_data.items():
            mock_doc = MockDocument(doc_id, self.name, self.firestore)
            mock_doc._data = data
            docs.append(mock_doc)
        return docs

class MockDocument:
    def __init__(self, doc_id, collection, firestore):
        self.id = doc_id
        self.collection = collection
        self.firestore = firestore
        self._data = None
        
    def set(self, data):
        if self.collection not in self.firestore.data:
            self.firestore.data[self.collection] = {}
        self.firestore.data[self.collection][self.id] = data
        logger.info(f"🔥 Mock Firestore: Set {self.collection}/{self.id}")
        
    def get(self):
        collection_data = self.firestore.data.get(self.collection, {})
        self._data = collection_data.get(self.id)
        return self
        
    def exists(self):
        collection_data = self.firestore.data.get(self.collection, {})
        return self.id in collection_data
        
    def to_dict(self):
        return self._data

# Initialize based on configuration
if USE_MOCK_LLM:
    llm = MockLLM()
    logger.info("🔮 Using Mock LLM for fast testing")
else:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    logger.info("🤖 Using Real OpenAI LLM")

if USE_MOCK_FIRESTORE:
    db = MockFirestore()
    logger.info("🔥 Using Mock Firestore for local testing")
else:
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("🔥 Using Real Firestore")

# Import agent processing logic
from oneNodeRemMem import process_message

class LocalAgentFirestoreLoop:
    def __init__(self):
        self.conversation_count = 0
        
    def create_task_key(self, user_email: str, task_title: str, timestamp: str = None) -> str:
        if not timestamp:
            timestamp = datetime.now().isoformat()
        return f"{user_email}_{task_title}_{timestamp}"
    
    def find_existing_task(self, user_email: str, task_title: str) -> Optional[Dict]:
        """Find existing task in Firestore"""
        try:
            if USE_MOCK_FIRESTORE:
                # Mock implementation
                collection_data = db.data.get('conversations', {})
                for doc_id, data in collection_data.items():
                    if (data.get('userEmail') == user_email and 
                        data.get('taskTitle') == task_title and
                        data.get('status') != 'completed'):
                        return {'taskKey': doc_id, 'taskData': data}
                return None
            else:
                # Real Firestore implementation
                task_agent_ref = db.collection('conversations')
                docs = task_agent_ref.stream()
                
                for doc in docs:
                    data = doc.to_dict()
                    if (data.get('userEmail') == user_email and 
                        data.get('taskTitle') == task_title and
                        data.get('status') != 'completed'):
                        return {'taskKey': doc.id, 'taskData': data}
                return None
        except Exception as error:
            logger.error(f'❌ Error finding existing task: {error}')
            return None
    
    def create_new_task(self, user_email: str, task_title: str, user_first_name: str = None) -> Dict:
        """Create new task in Firestore"""
        timestamp = datetime.now().isoformat()
        task_key = self.create_task_key(user_email, task_title, timestamp)
        
        conversation_state = {
            'taskId': task_key,
            'taskTitle': task_title,
            'userEmail': user_email,
            'userFirstName': user_first_name or user_email.split('@')[0],
            'createdAt': timestamp,
            'lastUpdated': timestamp,
            'status': 'active',
            'conversationHistory': [],
            'fullInputHistory': [],
            'turn_count': 0
        }
        
        db.collection('conversations').document(task_key).set(conversation_state)
        logger.info(f'✅ Created new conversation: {task_key}')
        
        return {'taskKey': task_key, 'taskData': conversation_state}
    
    def update_conversation_state(self, task_key: str, conversation_state: Dict, user_input: str, agent_result: Dict):
        """Update conversation state in Firestore"""
        timestamp = datetime.now().isoformat()
        
        # Update conversation history
        conversation_state['conversationHistory'].append({
            'userMessage': user_input,
            'agentResponse': agent_result.get('question', ''),
            'timestamp': timestamp,
            'turn_count': agent_result.get('turn_count', 0)
        })
        
        # Update metadata
        conversation_state['lastUpdated'] = timestamp
        conversation_state['turn_count'] = agent_result.get('turn_count', 0)
        if agent_result.get('is_complete'):
            conversation_state['status'] = 'completed'
            conversation_state['completion_state'] = agent_result.get('completion_state', 'OTHER')
        
        # Add full input history
        full_input = {
            'user_input': user_input,
            'previous_state': {
                'conversation_history': agent_result.get('conversation_history', ''),
                'is_complete': agent_result.get('is_complete', False),
                'turn_count': agent_result.get('turn_count', 0),
                'user_email': agent_result.get('user_email', '')
            }
        }
        
        conversation_state['fullInputHistory'].append({
            'input': full_input,
            'timestamp': timestamp,
            'turn_number': agent_result.get('turn_count', 0)
        })
        
        # Save to Firestore
        db.collection('conversations').document(task_key).set(conversation_state)
        logger.info(f'💾 Updated conversation state for {task_key}')
        
        return conversation_state
    
    async def run_conversation_turn(self, user_email: str, task_title: str, user_input: str, user_first_name: str = None) -> Dict:
        """Run a single conversation turn"""
        logger.info(f"🔄 Processing turn for {user_email}: '{user_input[:50]}...'")
        
        # Find or create task
        existing_task = self.find_existing_task(user_email, task_title)
        if existing_task:
            task_key = existing_task['taskKey']
            conversation_state = existing_task['taskData']
            logger.info(f"📂 Found existing task: {task_key}")
        else:
            new_task = self.create_new_task(user_email, task_title, user_first_name)
            task_key = new_task['taskKey']
            conversation_state = new_task['taskData']
            logger.info(f"📄 Created new task: {task_key}")
        
        # Check if conversation is already complete
        if conversation_state.get('status') == 'completed':
            logger.info(f"✅ Conversation already completed")
            return {
                'question': 'This conversation has already been completed.',
                'is_complete': True,
                'turn_count': conversation_state.get('turn_count', 0)
            }
        
        # Prepare previous state for agent
        previous_state = None
        if conversation_state.get('conversationHistory'):
            # Build conversation history string
            history_parts = []
            for entry in conversation_state['conversationHistory']:
                if entry.get('agentResponse'):
                    history_parts.append(f"Question: {entry['agentResponse']}")
                if entry.get('userMessage'):
                    history_parts.append(f"Learned: User said: {entry['userMessage']}")
            
            previous_state = {
                'conversation_history': '\n'.join(history_parts),
                'is_complete': False,
                'turn_count': conversation_state.get('turn_count', 0),
                'user_email': user_email
            }
        
        # Process with agent
        agent_input = {
            'user_input': user_input,
            'previous_state': previous_state,
            'user_email': user_email
        }
        
        logger.info(f"🤖 Calling agent with input...")
        agent_result = await process_message(agent_input)
        logger.info(f"✅ Agent response received: turn {agent_result.get('turn_count', 0)}")
        
        # Update conversation state
        updated_state = self.update_conversation_state(task_key, conversation_state, user_input, agent_result)
        
        return {
            'question': agent_result.get('question', ''),
            'is_complete': agent_result.get('is_complete', False),
            'turn_count': agent_result.get('turn_count', 0),
            'completion_state': agent_result.get('completion_state', 'OTHER'),
            'task_key': task_key,
            'conversation_history': agent_result.get('conversation_history', '')
        }
    
    async def run_scripted_conversation(self, user_email: str, task_title: str, script: List[str], user_first_name: str = None):
        """Run a complete scripted conversation for testing"""
        logger.info(f"🎬 Starting scripted conversation: {len(script)} inputs")
        logger.info(f"👤 User: {user_email} | 📋 Task: {task_title}")
        
        self.conversation_count += 1
        results = []
        
        for i, user_input in enumerate(script, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🎬 SCRIPTED TURN {i}/{len(script)}")
            logger.info(f"{'='*60}")
            
            result = await self.run_conversation_turn(user_email, task_title, user_input, user_first_name)
            results.append(result)
            
            logger.info(f"👤 User: '{user_input}'")
            logger.info(f"🤖 Agent: '{result.get('question', '')}'")
            logger.info(f"📊 Turn: {result.get('turn_count', 0)} | Complete: {result.get('is_complete', False)}")
            
            if result.get('is_complete'):
                logger.info(f"🏁 Conversation completed after {i} turns")
                logger.info(f"🎯 Completion state: {result.get('completion_state', 'OTHER')}")
                break
        
        return results

# Test scripts for different scenarios
TEST_SCRIPTS = {
    "happy_path": [
        "",  # Initial greeting
        "Yes, I'm ready to discuss my task",
        "Yes, I'll reach out to the contractor",
        "No concerns, everything looks good",
    ],
    "hesitant_user": [
        "",  # Initial greeting
        "I'm not sure if I'm ready",
        "Maybe, I need to think about it",
        "I have some budget concerns",
        "Ok, I'll move forward"
    ],
    "quick_complete": [
        "",  # Initial greeting
        "Yes ready",
        "Yes will contact"
    ]
}

async def main():
    """Main test function"""
    logger.info("🚀 Starting Local Agent-Firestore Loop Test")
    
    loop = LocalAgentFirestoreLoop()
    
    # Test different scenarios
    test_user = "test@example.com"
    test_name = "Test User"
    
    for scenario_name, script in TEST_SCRIPTS.items():
        logger.info(f"\n🎯 Testing scenario: {scenario_name}")
        task_title = f"Test Task - {scenario_name}"
        
        results = await loop.run_scripted_conversation(
            user_email=test_user,
            task_title=task_title,
            script=script,
            user_first_name=test_name
        )
        
        logger.info(f"✅ Scenario '{scenario_name}' completed with {len(results)} turns")
        
        # Show final conversation state
        if USE_MOCK_FIRESTORE:
            logger.info("📊 Final Firestore state:")
            for collection_name, collection_data in db.data.items():
                logger.info(f"  📁 {collection_name}: {len(collection_data)} documents")
        
        print(f"\n{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())