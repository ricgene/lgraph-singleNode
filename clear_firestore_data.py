#!/usr/bin/env python3
"""
Script to clear Firestore conversation data for testing
"""

import os
from google.cloud import firestore

def clear_conversation_data():
    """Clear conversation data from Firestore"""
    try:
        # Initialize Firestore client
        db = firestore.Client()
        
        # Delete the specific user document
        user_email = "richard.genet@gmail.com"
        doc_ref = db.collection('taskAgent1').document(user_email)
        
        # Check if document exists
        doc = doc_ref.get()
        if doc.exists:
            print(f"🗑️ Deleting conversation data for {user_email}")
            doc_ref.delete()
            print(f"✅ Successfully deleted conversation data for {user_email}")
        else:
            print(f"ℹ️ No conversation data found for {user_email}")
            
        # Also clear conversation_states collection if it exists
        states_ref = db.collection('conversation_states').document(user_email)
        states_doc = states_ref.get()
        if states_doc.exists:
            print(f"🗑️ Deleting conversation state for {user_email}")
            states_ref.delete()
            print(f"✅ Successfully deleted conversation state for {user_email}")
        else:
            print(f"ℹ️ No conversation state found for {user_email}")
            
    except Exception as e:
        print(f"❌ Error clearing data: {e}")

if __name__ == "__main__":
    clear_conversation_data() 