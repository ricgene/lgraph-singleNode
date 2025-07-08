#!/usr/bin/env python3
"""
Check Firestore for Task Records
"""

from google.cloud import firestore
import json
from datetime import datetime

def check_firestore():
    db = firestore.Client()
    
    print('🔍 Checking Firestore for Task Records')
    print('=' * 50)
    
    # Check tasks collection
    print('\n📋 Checking tasks collection:')
    tasks = list(db.collection('tasks').stream())
    print(f'Found {len(tasks)} task records')
    
    if tasks:
        print('\nRecent tasks:')
        for task in tasks[-3:]:  # Show last 3
            data = task.to_dict()
            print(f'  ID: {task.id}')
            print(f'  Customer Email: {data.get("custemail", "N/A")}')
            print(f'  Task: {data.get("Task", "N/A")}')
            print(f'  Created: {data.get("created_at", "N/A")}')
            print(f'  Source: {data.get("source", "N/A")}')
            print('  ---')
    
    # Check conversations collection
    print('\n💬 Checking conversations collection:')
    conversations = list(db.collection('conversations').stream())
    print(f'Found {len(conversations)} conversation records')
    
    if conversations:
        print('\nRecent conversations:')
        for conv in conversations[-3:]:  # Show last 3
            data = conv.to_dict()
            print(f'  ID: {conv.id}')
            print(f'  Customer Email: {data.get("customer_email", "N/A")}')
            print(f'  Task Title: {data.get("task_title", "N/A")}')
            print(f'  Created: {data.get("created_at", "N/A")}')
            print('  ---')
    
    # Check processedEmails collection
    print('\n📧 Checking processedEmails collection:')
    processed = list(db.collection('processedEmails').stream())
    print(f'Found {len(processed)} processed email records')
    
    if processed:
        print('\nRecent processed emails:')
        for email in processed[-3:]:  # Show last 3
            data = email.to_dict()
            print(f'  ID: {email.id}')
            print(f'  From: {data.get("from", "N/A")}')
            print(f'  Subject: {data.get("subject", "N/A")}')
            print(f'  Processed: {data.get("processedAt", "N/A")}')
            print('  ---')
    
    # Check telegram_users collection
    print('\n📱 Checking telegram_users collection:')
    telegram_users = list(db.collection('telegram_users').stream())
    print(f'Found {len(telegram_users)} telegram user records')
    
    if telegram_users:
        print('\nTelegram users:')
        for user in telegram_users:
            data = user.to_dict()
            print(f'  Username: {user.id}')
            print(f'  Chat ID: {data.get("chat_id", "N/A")}')
            print('  ---')
    
    print('\n✅ Database check completed!')

if __name__ == "__main__":
    check_firestore() 