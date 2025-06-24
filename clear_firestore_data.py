#!/usr/bin/env python3
"""
Simple Firestore Cleanup Script
Clears all conversation states and processed email tracking to start fresh.
"""

import os
import sys
from google.cloud import firestore

def clear_firestore_data():
    """Clear all email processing data from Firestore."""
    try:
        # Initialize Firestore client
        db = firestore.Client()
        
        print("🚀 Firestore Cleanup Script")
        print("=" * 50)
        
        # Collections to clear
        collections_to_clear = [
            'conversation_states',
            'processed_emails', 
            'email_locks',
            'email_processing_sessions'
        ]
        
        total_deleted = 0
        
        for collection_name in collections_to_clear:
            print(f"🧹 Clearing collection: {collection_name}")
            docs = list(db.collection(collection_name).stream())
            
            if docs:
                print(f"  Found {len(docs)} documents to delete")
                for doc in docs:
                    print(f"    Deleting: {doc.id}")
                    doc.reference.delete()
                total_deleted += len(docs)
                print(f"  ✅ Deleted {len(docs)} documents")
            else:
                print(f"  ℹ️ No documents found")
        
        print()
        print(f"✅ Cleanup completed! Total documents deleted: {total_deleted}")
        print("🎉 Your email processing system is now fresh and ready to start.")
        print()
        print("📧 You can now send a new email to test the system.")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)

def delete_task_collections():
    db = firestore.Client()
    collections = list(db.collections())
    task_collections = [col for col in collections if col.id.startswith('task')]
    if not task_collections:
        print("No collections starting with 'task' found.")
        return
    print("The following collections will be deleted:")
    for col in task_collections:
        print(f"- {col.id}")
    confirm = input("Are you sure you want to delete ALL documents in these collections? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return
    for col in task_collections:
        docs = list(col.stream())
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        print(f"Deleted {count} documents from collection '{col.id}'")
    print("Done.")

if __name__ == "__main__":
    clear_firestore_data()
    delete_task_collections() 