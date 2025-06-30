#!/usr/bin/env python3
"""
Simple Observability Module for Local Agent Testing
Provides structured logging and basic tracing
"""

import os
import json
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

class SimpleLogger:
    def __init__(self, name: str = "agent_test", log_file: str = None):
        self.name = name
        self.events = []
        self.log_file = log_file
        
        # Configure standard logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(console_handler)
    
    @contextmanager
    def trace_operation(self, operation: str, metadata: Dict[str, Any] = None):
        """Context manager for tracing operations with timing"""
        trace_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        self.logger.info(f"🚀 Starting {operation} | trace_id={trace_id}")
        
        try:
            yield trace_id
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"❌ Error in {operation}: {str(e)} | trace_id={trace_id} | duration={duration_ms:.2f}ms")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(f"✅ Completed {operation} | trace_id={trace_id} | duration={duration_ms:.2f}ms")
    
    def log_conversation_start(self, user_email: str, task_title: str, metadata: Dict[str, Any] = None):
        """Log conversation start event"""
        self.logger.info(f"🎬 Starting conversation | user={user_email} | task={task_title}")
    
    def log_conversation_turn(self, turn_number: int, user_input: str, agent_response: str, metadata: Dict[str, Any] = None):
        """Log conversation turn event"""
        self.logger.info(f"🔄 Turn {turn_number} | input_len={len(user_input)} | response_len={len(agent_response)}")
        self.logger.info(f"👤 User: '{user_input[:100]}...'")
        self.logger.info(f"🤖 Agent: '{agent_response[:100]}...'")
    
    def log_conversation_complete(self, total_turns: int, completion_state: str, metadata: Dict[str, Any] = None):
        """Log conversation completion event"""
        self.logger.info(f"🏁 Conversation completed | turns={total_turns} | state={completion_state}")
    
    def log_agent_call(self, input_data: Dict[str, Any], response_data: Dict[str, Any], duration_ms: float):
        """Log agent call with input/output"""
        self.logger.info(f"🤖 Agent call completed | turn={response_data.get('turn_count', 0)} | complete={response_data.get('is_complete', False)} | duration={duration_ms:.2f}ms")
    
    def log_firestore_operation(self, operation: str, collection: str, document_id: str, 
                               data_size: int = None, duration_ms: float = None):
        """Log Firestore operations"""
        size_info = f" | size={data_size}b" if data_size else ""
        duration_info = f" | duration={duration_ms:.2f}ms" if duration_ms else ""
        self.logger.info(f"🔥 Firestore {operation} | {collection}/{document_id}{size_info}{duration_info}")
    
    def log_llm_call(self, model: str, input_tokens: int = None, output_tokens: int = None, 
                     duration_ms: float = None, cost_estimate: float = None):
        """Log LLM API calls"""
        token_info = f" | tokens_in={input_tokens} | tokens_out={output_tokens}" if input_tokens else ""
        cost_info = f" | cost=${cost_estimate:.4f}" if cost_estimate else ""
        duration_info = f" | duration={duration_ms:.2f}ms" if duration_ms else ""
        self.logger.info(f"🔮 LLM call | model={model}{token_info}{cost_info}{duration_info}")
    
    def export_trace_summary(self):
        """Export a simple summary"""
        return {
            "timestamp": datetime.now().isoformat(),
            "test_completed": True,
            "log_entries": len(self.events)
        }
    
    def save_trace_report(self, filename: str = None, output_dir: str = None):
        """Save a simple trace report"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trace_report_{timestamp}.json"
        
        # Use output directory if provided
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
        else:
            filepath = filename
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_completed": True,
            "log_entries": len(self.events),
            "test_summary": f"Ran {len(self.events)} operations successfully"
        }
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"📊 Trace report saved to {filepath}")
        return filepath

# Global logger instance
_global_logger = None

def get_logger(name: str = "agent_test", log_file: str = None) -> SimpleLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = SimpleLogger(name, log_file)
    return _global_logger

# For backward compatibility with the complex version
LogLevel = SimpleLogger
EventType = SimpleLogger