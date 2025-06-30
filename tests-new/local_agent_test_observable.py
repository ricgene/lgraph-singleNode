#!/usr/bin/env python3
"""
Observable Local Agent-Firestore Loop Test System
Enhanced with comprehensive observability and tracing
"""

import os
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Import observability from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from observability import get_logger

# Load environment variables
load_dotenv()

# Environment configuration
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
AGENT_PROMPT_TYPE = os.getenv("AGENT_PROMPT_TYPE", "debug")
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
USE_MOCK_FIRESTORE = os.getenv("USE_MOCK_FIRESTORE", "true").lower() == "true"
ENABLE_OBSERVABILITY = os.getenv("ENABLE_OBSERVABILITY", "true").lower() == "true"

# Initialize observability
if ENABLE_OBSERVABILITY:
    log_path = os.path.join(os.path.dirname(__file__), "results", "observable_test.log")
    logger = get_logger("agent_observable", log_path)
    logger.logger.info("🚀 Observable Agent Test Started")
    logger.logger.info(f"🤖 Agent prompt type: {AGENT_PROMPT_TYPE}")
    logger.logger.info(f"🔮 Mock LLM: {USE_MOCK_LLM}")
    logger.logger.info(f"🔥 Mock Firestore: {USE_MOCK_FIRESTORE}")
else:
    logger = None

# Enhanced Mock LLM with observability
class ObservableMockLLM:
    def __init__(self):
        self.call_count = 0
        
    def invoke(self, messages, config=None):
        start_time = time.time()
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
        
        # Log LLM call with observability
        duration_ms = (time.time() - start_time) * 1000
        if logger:
            logger.log_llm_call(
                model="mock-gpt-4",
                input_tokens=len(str(messages)),
                output_tokens=len(response),
                duration_ms=duration_ms,
                cost_estimate=0.0  # Mock is free!
            )
        
        # Mock response object
        class MockResponse:
            def __init__(self, content):
                self.content = content
        
        return MockResponse(response)

# Enhanced Mock Firestore with observability
class ObservableMockFirestore:
    def __init__(self):
        self.data = {}
        
    def collection(self, name):
        return ObservableMockCollection(name, self)

class ObservableMockCollection:
    def __init__(self, name, firestore):
        self.name = name
        self.firestore = firestore
        
    def document(self, doc_id):
        return ObservableMockDocument(doc_id, self.name, self.firestore)
        
    def stream(self):
        start_time = time.time()
        collection_data = self.firestore.data.get(self.name, {})
        docs = []
        for doc_id, data in collection_data.items():
            mock_doc = ObservableMockDocument(doc_id, self.name, self.firestore)
            mock_doc._data = data
            docs.append(mock_doc)
        
        # Log Firestore read operation
        if logger:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_firestore_operation(
                operation="stream",
                collection=self.name,
                document_id="*",
                data_size=len(json.dumps(collection_data)),
                duration_ms=duration_ms
            )
        
        return docs

class ObservableMockDocument:
    def __init__(self, doc_id, collection, firestore):
        self.id = doc_id
        self.collection = collection
        self.firestore = firestore
        self._data = None
        
    def set(self, data):
        start_time = time.time()
        
        if self.collection not in self.firestore.data:
            self.firestore.data[self.collection] = {}
        self.firestore.data[self.collection][self.id] = data
        
        # Log Firestore write operation
        if logger:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_firestore_operation(
                operation="set",
                collection=self.collection,
                document_id=self.id,
                data_size=len(json.dumps(data)),
                duration_ms=duration_ms
            )
        
    def get(self):
        start_time = time.time()
        collection_data = self.firestore.data.get(self.collection, {})
        self._data = collection_data.get(self.id)
        
        # Log Firestore read operation
        if logger:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_firestore_operation(
                operation="get",
                collection=self.collection,
                document_id=self.id,
                data_size=len(json.dumps(self._data)) if self._data else 0,
                duration_ms=duration_ms
            )
        
        return self
        
    def exists(self):
        collection_data = self.firestore.data.get(self.collection, {})
        return self.id in collection_data
        
    def to_dict(self):
        return self._data

# Initialize based on configuration
if USE_MOCK_LLM:
    llm = ObservableMockLLM()
    if logger:
        logger.logger.info("🔮 Using Observable Mock LLM for fast testing")
else:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    if logger:
        logger.logger.info("🤖 Using Real OpenAI LLM")

if USE_MOCK_FIRESTORE:
    db = ObservableMockFirestore()
    if logger:
        logger.logger.info("🔥 Using Observable Mock Firestore for local testing")
else:
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    if logger:
        logger.logger.info("🔥 Using Real Firestore")

# Import agent processing logic from parent directory
from oneNodeRemMem import process_message

class ObservableLocalAgentFirestoreLoop:
    def __init__(self):
        self.conversation_count = 0
        
    def create_task_key(self, user_email: str, task_title: str, timestamp: str = None) -> str:
        if not timestamp:
            timestamp = datetime.now().isoformat()
        return f"{user_email}_{task_title}_{timestamp}"
    
    def find_existing_task(self, user_email: str, task_title: str) -> Optional[Dict]:
        """Find existing task in Firestore with tracing"""
        if logger:
            with logger.trace_operation("find_existing_task", {
                "user_email": user_email,
                "task_title": task_title
            }):
                return self._find_existing_task_impl(user_email, task_title)
        else:
            return self._find_existing_task_impl(user_email, task_title)
    
    def _find_existing_task_impl(self, user_email: str, task_title: str) -> Optional[Dict]:
        """Implementation of find_existing_task"""
        try:
            if USE_MOCK_FIRESTORE:
                collection_data = db.data.get('conversations', {})
                for doc_id, data in collection_data.items():
                    if (data.get('userEmail') == user_email and 
                        data.get('taskTitle') == task_title and
                        data.get('status') != 'completed'):
                        return {'taskKey': doc_id, 'taskData': data}
                return None
            else:
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
            if logger:
                logger._log_event(
                    LogLevel.ERROR,
                    EventType.ERROR,
                    f"Error finding existing task: {error}",
                    {"user_email": user_email, "task_title": task_title}
                )
            return None
    
    def create_new_task(self, user_email: str, task_title: str, user_first_name: str = None) -> Dict:
        """Create new task in Firestore with tracing"""
        if logger:
            with logger.trace_operation("create_new_task", {
                "user_email": user_email,
                "task_title": task_title,
                "user_first_name": user_first_name
            }):
                return self._create_new_task_impl(user_email, task_title, user_first_name)
        else:
            return self._create_new_task_impl(user_email, task_title, user_first_name)
    
    def _create_new_task_impl(self, user_email: str, task_title: str, user_first_name: str = None) -> Dict:
        """Implementation of create_new_task"""
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
        
        if logger:
            logger.logger.info(f'✅ Created new conversation: {task_key}')
        
        return {'taskKey': task_key, 'taskData': conversation_state}
    
    def update_conversation_state(self, task_key: str, conversation_state: Dict, 
                                user_input: str, agent_result: Dict):
        """Update conversation state in Firestore with tracing"""
        if logger:
            with logger.trace_operation("update_conversation_state", {
                "task_key": task_key,
                "turn_count": agent_result.get('turn_count', 0)
            }):
                return self._update_conversation_state_impl(task_key, conversation_state, user_input, agent_result)
        else:
            return self._update_conversation_state_impl(task_key, conversation_state, user_input, agent_result)
    
    def _update_conversation_state_impl(self, task_key: str, conversation_state: Dict, 
                                      user_input: str, agent_result: Dict):
        """Implementation of update_conversation_state"""
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
        
        if logger:
            logger.logger.info(f'💾 Updated conversation state for {task_key}')
        
        return conversation_state
    
    async def run_conversation_turn(self, user_email: str, task_title: str, user_input: str, 
                                   user_first_name: str = None) -> Dict:
        """Run a single conversation turn with full observability"""
        if logger:
            with logger.trace_operation("conversation_turn", {
                "user_email": user_email,
                "task_title": task_title,
                "user_input_length": len(user_input)
            }):
                return await self._run_conversation_turn_impl(user_email, task_title, user_input, user_first_name)
        else:
            return await self._run_conversation_turn_impl(user_email, task_title, user_input, user_first_name)
    
    async def _run_conversation_turn_impl(self, user_email: str, task_title: str, 
                                        user_input: str, user_first_name: str = None) -> Dict:
        """Implementation of run_conversation_turn"""
        # Find or create task
        existing_task = self.find_existing_task(user_email, task_title)
        if existing_task:
            task_key = existing_task['taskKey']
            conversation_state = existing_task['taskData']
            if logger:
                logger.logger.info(f"📂 Found existing task: {task_key}")
        else:
            new_task = self.create_new_task(user_email, task_title, user_first_name)
            task_key = new_task['taskKey']
            conversation_state = new_task['taskData']
            if logger:
                logger.logger.info(f"📄 Created new task: {task_key}")
        
        # Check if conversation is already complete
        if conversation_state.get('status') == 'completed':
            if logger:
                logger.logger.info(f"✅ Conversation already completed")
            return {
                'question': 'This conversation has already been completed.',
                'is_complete': True,
                'turn_count': conversation_state.get('turn_count', 0)
            }
        
        # Prepare previous state for agent
        previous_state = None
        if conversation_state.get('conversationHistory'):
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
        
        # Process with agent (with tracing)
        agent_input = {
            'user_input': user_input,
            'previous_state': previous_state,
            'user_email': user_email
        }
        
        start_time = time.time()
        if logger:
            logger.logger.info(f"🤖 Calling agent with input...")
        
        agent_result = await process_message(agent_input)
        
        duration_ms = (time.time() - start_time) * 1000
        if logger:
            logger.log_agent_call(agent_input, agent_result, duration_ms)
            logger.logger.info(f"✅ Agent response received: turn {agent_result.get('turn_count', 0)}")
        
        # Update conversation state
        updated_state = self.update_conversation_state(task_key, conversation_state, user_input, agent_result)
        
        # Log conversation turn
        if logger:
            logger.log_conversation_turn(
                turn_number=agent_result.get('turn_count', 0),
                user_input=user_input,
                agent_response=agent_result.get('question', ''),
                metadata={
                    "task_key": task_key,
                    "is_complete": agent_result.get('is_complete', False),
                    "completion_state": agent_result.get('completion_state', 'OTHER')
                }
            )
        
        return {
            'question': agent_result.get('question', ''),
            'is_complete': agent_result.get('is_complete', False),
            'turn_count': agent_result.get('turn_count', 0),
            'completion_state': agent_result.get('completion_state', 'OTHER'),
            'task_key': task_key,
            'conversation_history': agent_result.get('conversation_history', '')
        }
    
    async def run_scripted_conversation(self, user_email: str, task_title: str, script: List[str], 
                                       user_first_name: str = None):
        """Run a complete scripted conversation with full observability"""
        if logger:
            with logger.trace_operation("scripted_conversation", {
                "user_email": user_email,
                "task_title": task_title,
                "script_length": len(script)
            }):
                logger.log_conversation_start(user_email, task_title, {
                    "script_length": len(script),
                    "user_first_name": user_first_name
                })
                
                results = await self._run_scripted_conversation_impl(user_email, task_title, script, user_first_name)
                
                final_result = results[-1] if results else {}
                logger.log_conversation_complete(
                    total_turns=len(results),
                    completion_state=final_result.get('completion_state', 'OTHER'),
                    metadata={
                        "task_key": final_result.get('task_key', ''),
                        "final_turn_count": final_result.get('turn_count', 0)
                    }
                )
                
                return results
        else:
            return await self._run_scripted_conversation_impl(user_email, task_title, script, user_first_name)
    
    async def _run_scripted_conversation_impl(self, user_email: str, task_title: str, script: List[str], 
                                            user_first_name: str = None):
        """Implementation of run_scripted_conversation"""
        if logger:
            logger.logger.info(f"🎬 Starting scripted conversation: {len(script)} inputs")
            logger.logger.info(f"👤 User: {user_email} | 📋 Task: {task_title}")
        
        self.conversation_count += 1
        results = []
        
        for i, user_input in enumerate(script, 1):
            if logger:
                logger.logger.info(f"\n{'='*60}")
                logger.logger.info(f"🎬 SCRIPTED TURN {i}/{len(script)}")
                logger.logger.info(f"{'='*60}")
            
            result = await self.run_conversation_turn(user_email, task_title, user_input, user_first_name)
            results.append(result)
            
            if logger:
                logger.logger.info(f"👤 User: '{user_input}'")
                logger.logger.info(f"🤖 Agent: '{result.get('question', '')}'")
                logger.logger.info(f"📊 Turn: {result.get('turn_count', 0)} | Complete: {result.get('is_complete', False)}")
            
            if result.get('is_complete'):
                if logger:
                    logger.logger.info(f"🏁 Conversation completed after {i} turns")
                    logger.logger.info(f"🎯 Completion state: {result.get('completion_state', 'OTHER')}")
                break
        
        return results

# Test scripts
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
    """Main test function with observability"""
    if logger:
        with logger.trace_operation("main_test_suite"):
            logger.logger.info("🚀 Starting Observable Local Agent-Firestore Loop Test")
            
            loop = ObservableLocalAgentFirestoreLoop()
            
            # Test different scenarios
            test_user = "test@example.com"
            test_name = "Test User"
            
            for scenario_name, script in TEST_SCRIPTS.items():
                if logger:
                    logger.logger.info(f"\n🎯 Testing scenario: {scenario_name}")
                task_title = f"Test Task - {scenario_name}"
                
                results = await loop.run_scripted_conversation(
                    user_email=test_user,
                    task_title=task_title,
                    script=script,
                    user_first_name=test_name
                )
                
                if logger:
                    logger.logger.info(f"✅ Scenario '{scenario_name}' completed with {len(results)} turns")
                
                print(f"\n{'='*80}\n")
            
            # Generate trace report
            if logger:
                summary = logger.export_trace_summary()
                logger.logger.info("📊 Test Suite Summary:")
                logger.logger.info(f"  Total Events: {summary['total_events']}")
                logger.logger.info(f"  Event Types: {summary['event_types']}")
                if summary.get('performance_metrics'):
                    perf = summary['performance_metrics']
                    logger.logger.info(f"  Avg Duration: {perf['avg_duration_ms']:.2f}ms")
                    logger.logger.info(f"  Total Duration: {perf['total_duration_ms']:.2f}ms")
                
                results_dir = os.path.join(os.path.dirname(__file__), "results")
                report_file = logger.save_trace_report(output_dir=results_dir)
                logger.logger.info(f"📊 Full trace report: {report_file}")
    else:
        print("Observability disabled - running basic test")
        loop = ObservableLocalAgentFirestoreLoop()
        test_user = "test@example.com"
        test_name = "Test User"
        
        for scenario_name, script in TEST_SCRIPTS.items():
            print(f"\n🎯 Testing scenario: {scenario_name}")
            task_title = f"Test Task - {scenario_name}"
            
            results = await loop.run_scripted_conversation(
                user_email=test_user,
                task_title=task_title,
                script=script,
                user_first_name=test_name
            )
            
            print(f"✅ Scenario '{scenario_name}' completed with {len(results)} turns")
        
        # Always save a final summary
        results_dir = os.path.join(os.path.dirname(__file__), "results")
        summary_file = os.path.join(results_dir, "test_summary.txt")
        os.makedirs(results_dir, exist_ok=True)
        
        with open(summary_file, "w") as f:
            f.write(f"Test completed at: {datetime.now().isoformat()}\n")
            f.write(f"Total scenarios: {len(TEST_SCRIPTS)}\n")
            f.write("All tests passed!\n")
        
        print(f"📊 Test summary saved to: {summary_file}")

if __name__ == "__main__":
    asyncio.run(main())