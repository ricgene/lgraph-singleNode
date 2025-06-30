#!/bin/bash
# Cleanup Script for Obsolete Files
# Review before running - will move files to cleanup/ directory first

echo "🧹 Cleanup Obsolete Files Script"
echo "================================"

# Create cleanup directory for review
CLEANUP_DIR="cleanup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CLEANUP_DIR"

echo "📁 Created cleanup directory: $CLEANUP_DIR"
echo "Files will be moved here for review before deletion"

# Function to move file/directory to cleanup
move_to_cleanup() {
    local item="$1"
    if [[ -e "$item" ]]; then
        echo "📦 Moving: $item"
        mv "$item" "$CLEANUP_DIR/"
    else
        echo "⚠️  Not found: $item"
    fi
}

echo -e "\n🗂️  PHASE 1: Old Test Files"
move_to_cleanup "tests/conversation_log_20250627_161319.json"
move_to_cleanup "tests/conversation_log_20250627_173107.json"
move_to_cleanup "tests/conversation_log_20250627_173303.json"
move_to_cleanup "tests/old-cloud"
move_to_cleanup "processed_emails.json"
move_to_cleanup "simple_conversation_states.json"

echo -e "\n🗂️  PHASE 2: Legacy Scripts"
move_to_cleanup "create_test_user.js"
move_to_cleanup "exchange_token.js"
move_to_cleanup "get_firebase_token.js"
move_to_cleanup "get_service_account_token.js"
move_to_cleanup "simple_token.py"
move_to_cleanup "test_parsing.py"

echo -e "\n🗂️  PHASE 3: Development/Debug Files"
move_to_cleanup "langgraph_server.log"
move_to_cleanup "real_test.sh"
move_to_cleanup "quick_sms_test.py"

echo -e "\n🗂️  PHASE 4: Old Email System (Review Before Moving)"
echo "⚠️  Skipping email_langgraph_integration.js - may still be needed"
echo "⚠️  Skipping langgraph_server.py - may still be needed"

echo -e "\n✅ Cleanup completed!"
echo "📋 Review files in $CLEANUP_DIR/"
echo "🗑️  If everything looks good, run: rm -rf $CLEANUP_DIR"
echo "🔄 If you need something back, run: mv $CLEANUP_DIR/filename ."

# List what was moved
echo -e "\n📊 Files moved to cleanup:"
ls -la "$CLEANUP_DIR/" 2>/dev/null || echo "No files were moved"

# Show current directory size difference
echo -e "\n📈 Directory cleanup summary:"
du -sh . 2>/dev/null | awk '{print "Current size: " $1}'
du -sh "$CLEANUP_DIR" 2>/dev/null | awk '{print "Cleaned files: " $1}'