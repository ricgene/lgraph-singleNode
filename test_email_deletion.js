#!/usr/bin/env node
/**
 * Test Email Deletion Functionality
 * 
 * This script tests the email deletion logic to ensure emails are properly
 * deleted after processing to prevent duplicates.
 */

const Imap = require('imap');
const { simpleParser } = require('mailparser');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;

console.log('🧪 Testing Email Deletion Functionality');
console.log('=' * 50);

// IMAP connection
function createImapConnection() {
  return new Imap({
    user: GMAIL_USER,
    password: GMAIL_APP_PASSWORD,
    host: 'imap.gmail.com',
    port: 993,
    tls: true,
    tlsOptions: { rejectUnauthorized: false }
  });
}

// Test email deletion
async function testEmailDeletion() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    
    imap.once('ready', () => {
      console.log('✅ IMAP connection ready');
      
      imap.openBox('INBOX', false, (err, box) => {
        if (err) {
          console.error('❌ Error opening INBOX:', err);
          imap.end();
          reject(err);
          return;
        }
        
        console.log(`📧 INBOX opened. Total messages: ${box.messages.total}`);
        
        // Search for recent emails (last 5)
        imap.search(['ALL'], (err, results) => {
          if (err) {
            console.error('❌ Search error:', err);
            imap.end();
            reject(err);
            return;
          }
          
          if (results.length === 0) {
            console.log('ℹ️ No emails found in INBOX');
            imap.end();
            resolve();
            return;
          }
          
          const recentEmails = results.slice(-5);
          console.log(`📋 Found ${recentEmails.length} recent emails to check`);
          
          let processedCount = 0;
          const fetch = imap.fetch(recentEmails, { bodies: '', struct: true });
          
          fetch.on('message', (msg, seqno) => {
            let uid = null;
            let subject = '';
            let from = '';
            
            msg.on('attributes', (attrs) => {
              uid = attrs.uid;
              subject = attrs.envelope?.subject || 'No subject';
              from = attrs.envelope?.from?.[0]?.address || 'Unknown';
            });
            
            msg.on('body', async (stream) => {
              try {
                const parsed = await simpleParser(stream);
                const messageId = parsed.messageId;
                
                console.log(`\n📧 Email ${seqno}:`);
                console.log(`   UID: ${uid}`);
                console.log(`   From: ${from}`);
                console.log(`   Subject: ${subject}`);
                console.log(`   Message-ID: ${messageId}`);
                
                // Check if this looks like a task email
                const isTaskEmail = subject.toLowerCase().includes('task') || 
                                  parsed.text?.toLowerCase().includes('task') ||
                                  from.includes('helen');
                
                if (isTaskEmail) {
                  console.log(`   🎯 Detected as task email`);
                  
                  // Simulate the deletion process
                  console.log(`   🗑️ Testing deletion for UID: ${uid}`);
                  
                  try {
                    // Mark as deleted
                    await new Promise((resolve, reject) => {
                      imap.addFlags(uid, '\\Deleted', (err) => {
                        if (err) {
                          console.error(`   ❌ Failed to mark for deletion: ${err.message}`);
                          reject(err);
                        } else {
                          console.log(`   ✅ Marked for deletion`);
                          resolve();
                        }
                      });
                    });
                    
                    // Expunge (permanently delete)
                    await new Promise((resolve, reject) => {
                      imap.expunge((err) => {
                        if (err) {
                          console.error(`   ❌ Failed to expunge: ${err.message}`);
                          reject(err);
                        } else {
                          console.log(`   🗑️ Successfully deleted email UID: ${uid}`);
                          resolve();
                        }
                      });
                    });
                    
                  } catch (deleteError) {
                    console.error(`   ❌ Deletion failed: ${deleteError.message}`);
                  }
                } else {
                  console.log(`   ⏭️ Not a task email - skipping`);
                }
                
                processedCount++;
                if (processedCount >= recentEmails.length) {
                  console.log('\n✅ Finished processing emails');
                  imap.end();
                  resolve();
                }
                
              } catch (error) {
                console.error(`❌ Error processing email ${seqno}:`, error);
                processedCount++;
                if (processedCount >= recentEmails.length) {
                  imap.end();
                  resolve();
                }
              }
            });
          });
          
          fetch.once('error', (err) => {
            console.error('❌ Fetch error:', err);
            imap.end();
            reject(err);
          });
        });
      });
    });
    
    imap.once('error', (err) => {
      console.error('❌ IMAP connection error:', err);
      reject(err);
    });
    
    imap.once('end', () => {
      console.log('🔚 IMAP connection ended');
      resolve();
    });
    
    imap.connect();
  });
}

// Run the test
async function main() {
  try {
    console.log('🚀 Starting email deletion test...');
    await testEmailDeletion();
    console.log('\n✅ Test completed successfully');
  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { testEmailDeletion }; 