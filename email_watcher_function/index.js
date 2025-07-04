const Imap = require('imap');
const { simpleParser } = require('mailparser');
const { PubSub } = require('@google-cloud/pubsub');
const { Firestore } = require('@google-cloud/firestore');
const axios = require('axios');
require('dotenv').config();

const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;
const TOPIC_NAME = 'incoming-messages';
const UNIFIED_TASK_PROCESSOR_URL = process.env.UNIFIED_TASK_PROCESSOR_URL || 'https://unified-task-processor-cs64iuly6q-uc.a.run.app';

const firestore = new Firestore();
const COLLECTION = 'processedEmails';
const pubsub = new PubSub();

console.log('Gmail User:', GMAIL_USER);
console.log('Starting email watcher function...');

// Firestore helpers with enhanced logging
async function isProcessed(messageId) {
  if (!messageId) return false;
  try {
    const doc = await firestore.collection(COLLECTION).doc(messageId).get();
    if (doc.exists) {
      console.log(`ℹ️ Message-ID ${messageId} found in Firestore (already processed)`);
      return true;
    }
    console.log(`ℹ️ Message-ID ${messageId} not found in Firestore (not processed)`);
    return false;
  } catch (err) {
    console.error(`❌ Firestore error checking processed status for ${messageId}: ${err.message}`);
    // Fail safe: treat as not processed to avoid missing emails
    return false;
  }
}

async function markProcessed(messageId, meta = {}) {
  if (!messageId) return;
  try {
    await firestore.collection(COLLECTION).doc(messageId).set({
      processedAt: new Date().toISOString(),
      ...meta
    });
    console.log(`✅ Marked as processed in Firestore: ${messageId}`);
  } catch (err) {
    console.error(`❌ Firestore error marking processed for ${messageId}: ${err.message}`);
  }
}

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

// Helper functions for task creation email detection
function checkIfTaskCreationEmail(parsed) {
  // Check if email contains task-related keywords in subject or body
  const subject = parsed.subject?.toLowerCase() || '';
  const text = parsed.text?.toLowerCase() || '';
  const html = parsed.html?.toLowerCase() || '';
  
  // Keywords that indicate a task creation email
  const taskKeywords = [
    'new task',
    'task creation',
    'customer name',
    'task budget',
    'due date',
    'full address',
    'category',
    'vendors',
    'your new task'  // Existing filter keyword
  ];
  
  // Check if email contains task creation indicators
  const emailContent = `${subject} ${text} ${html}`;
  
  return taskKeywords.some(keyword => emailContent.includes(keyword)) ||
         // Check for structured task data patterns
         emailContent.includes('customer name:') ||
         emailContent.includes('task:') ||
         emailContent.includes('budget:') ||
         emailContent.includes('address:');
}

function extractTaskDataFromEmail(parsed, userEmail) {
  // Extract task data from email content
  const text = parsed.text || '';
  const html = parsed.html || '';
  const content = text || html;
  
  // Initialize task data structure
  const taskData = {
    custemail: userEmail,
    source: 'email',
    emailSubject: parsed.subject,
    emailDate: parsed.date,
    rawContent: content
  };
  
  // Extract common task fields using regex patterns
  const patterns = {
    'Customer Name': /customer\s*name\s*:?\s*([^\n\r]+)/i,
    'Task': /task\s*:?\s*([^\n\r]+)/i,
    'Task Budget': /(?:task\s*)?budget\s*:?\s*([^\n\r]+)/i,
    'Category': /category\s*:?\s*([^\n\r]+)/i,
    'DueDate': /due\s*date\s*:?\s*([^\n\r]+)/i,
    'Posted': /posted\s*:?\s*([^\n\r]+)/i,
    'FullAddress': /(?:full\s*)?address\s*:?\s*([^\n\r]+)/i,
    'Full Address': /full\s*address\s*:?\s*([^\n\r]+)/i,
    'State': /state\s*:?\s*([^\n\r]+)/i,
    'Phone': /phone\s*(?:number)?\s*:?\s*([^\n\r]+)/i,
    'vendors': /vendors?\s*:?\s*([^\n\r]+)/i
  };
  
  // Extract data using patterns
  for (const [field, pattern] of Object.entries(patterns)) {
    const match = content.match(pattern);
    if (match && match[1]) {
      taskData[field] = match[1].trim();
    }
  }
  
  // Set default values if not found
  if (!taskData['Customer Name']) {
    taskData['Customer Name'] = userEmail.split('@')[0]; // Use email prefix as fallback
  }
  
  if (!taskData['Task']) {
    taskData['Task'] = parsed.subject || 'Email Task';
  }
  
  // Set description from email content
  taskData.description = content.substring(0, 500); // First 500 chars as description
  
  console.log('Extracted task data:', JSON.stringify(taskData, null, 2));
  
  return taskData;
}

// Main email processing
async function processEmail(imap, stream, info) {
  try {
    const parsed = await simpleParser(stream);
    const messageId = parsed.messageId;
    const from = parsed.from?.value?.[0]?.address;
    const subject = parsed.subject;
    const text = parsed.text || '';
    const uid = info.uid;

    if (!messageId) {
      console.log('No Message-ID found, skipping.');
      return;
    }

    // Firestore deduplication with logging
    if (await isProcessed(messageId)) {
      console.log(`🚫 Already processed: ${messageId}`);
      return;
    }

    // Skip emails from our own address
    if (from === GMAIL_USER) {
      console.log('🚫 Skipping email from our own address:', from);
      return;
    }

    console.log(`📧 Processing email from: ${from}`);
    console.log(`📧 Subject: ${subject}`);
    console.log(`📝 Text preview: ${text.substring(0, 100)}...`);

    // Check if this is a task creation email
    const isTaskCreationEmail = checkIfTaskCreationEmail(parsed);
    
    let processingSuccess = false;
    
    if (isTaskCreationEmail) {
      console.log('📋 Detected task creation email - processing via unified task processor');
      
      try {
        // Extract task data from email
        const taskData = extractTaskDataFromEmail(parsed, from);
        
        // Call unified task processor
        const response = await axios.post(UNIFIED_TASK_PROCESSOR_URL, taskData, {
          headers: { 'Content-Type': 'application/json' },
          timeout: 30000 // 30 second timeout
        });
        
        if (response.status === 200) {
          console.log('✅ Task created successfully via unified processor:', response.data);
          processingSuccess = true;
        } else {
          console.error('❌ Failed to create task via unified processor:', response.status, response.data);
        }
      } catch (error) {
        console.error('❌ Error calling unified task processor:', error.message);
      }
    } else {
      // Legacy: Check for "your new task" emails and publish to Pub/Sub
      if (subject && subject.toLowerCase().includes('your new task')) {
        console.log('💬 Processing as legacy task email via Pub/Sub');
        
        const message = {
          userEmail: from,
          userResponse: text,
          taskTitle: subject,
          timestamp: new Date().toISOString(),
          messageId: messageId
        };

        try {
          const messageBuffer = Buffer.from(JSON.stringify(message));
          const publishedId = await pubsub.topic(TOPIC_NAME).publish(messageBuffer);
          console.log('✅ Published message', publishedId);
          processingSuccess = true;
        } catch (error) {
          console.error('❌ Failed to publish to Pub/Sub:', error);
        }
      } else {
        console.log(`⏭️ Skipping email - not a task creation email. Subject: ${subject}`);
        return; // Don't process or delete non-task emails
      }
    }
    
    if (processingSuccess) {
      // Mark as processed in Firestore
      await markProcessed(messageId, { from, subject, taskCreation: isTaskCreationEmail });
      
      // Delete email after successful processing to prevent duplicates
      if (uid) {
        try {
          console.log(`🗑️ Deleting email UID: ${uid}`);
          
          // Mark email as deleted
          await new Promise((resolve, reject) => {
            imap.addFlags(uid, '\\Deleted', (err) => {
              if (err) {
                console.error('❌ Failed to mark email for deletion:', err);
                reject(err);
              } else {
                console.log('✅ Marked email for deletion - UID:', uid);
                resolve();
              }
            });
          });
          
          // Expunge (permanently delete) the email
          await new Promise((resolve, reject) => {
            imap.expunge((err) => {
              if (err) {
                console.error('❌ Failed to expunge deleted email:', err);
                reject(err);
              } else {
                console.log('🗑️ Successfully deleted email UID:', uid);
                resolve();
              }
            });
          });
          
        } catch (deleteError) {
          console.error('❌ Error deleting email:', deleteError);
          // Continue processing even if deletion fails
        }
      } else {
        console.log('⚠️ Could not delete email (no UID available) - relying on Firestore tracking');
      }
    }
    
  } catch (error) {
    console.error('❌ Error processing email:', error);
  }
}

// List folders for debugging
function listFolders(imap) {
  return new Promise((resolve, reject) => {
    imap.getBoxes((err, boxes) => {
      if (err) {
        console.error('Error listing folders:', err);
        reject(err);
        return;
      }
      console.log('📁 Available folders:');
      function printBoxes(boxes, prefix = '') {
        for (const [name, box] of Object.entries(boxes)) {
          console.log(`${prefix}${name}: ${box.path}`);
          if (box.children) {
            printBoxes(box.children, prefix + '  ');
          }
        }
      }
      printBoxes(boxes);
      resolve(boxes);
    });
  });
}

// Main check function
async function checkEmails() {
  return new Promise((resolve, reject) => {
    const imap = createImapConnection();
    let pendingOperations = 0;

    imap.once('ready', async () => {
      console.log('IMAP connection ready');
      try {
        await listFolders(imap);
        imap.openBox('INBOX', false, (err, box) => {
          if (err) {
            console.error('Error opening INBOX:', err);
            imap.end();
            resolve();
            return;
          }
          console.log('Checking folder: INBOX');
          imap.search(['ALL'], (err, results) => {
            if (err) {
              console.error('Search error in INBOX:', err);
              imap.end();
              resolve();
              return;
            }
            if (results.length === 0) {
              console.log('No emails found in INBOX');
              imap.end();
              resolve();
              return;
            }
            console.log(`Found ${results.length} emails in INBOX`);
            const recentEmails = results.slice(-10);
            console.log(`Processing ${recentEmails.length} most recent emails`);
            const fetch = imap.fetch(recentEmails, { bodies: '', struct: true, extensions: true });
            fetch.on('message', (msg, seqno) => {
              let uid = null;
              msg.on('attributes', (attrs) => {
                uid = attrs.uid;
              });
              msg.on('body', (stream, info) => {
                pendingOperations++;
                processEmail(imap, stream, { uid: uid, seqno: seqno }).finally(() => {
                  pendingOperations--;
                  if (pendingOperations === 0) {
                    setTimeout(() => {
                      console.log('Finished processing INBOX');
                      imap.end();
                      resolve();
                    }, 2000);
                  }
                });
              });
            });
            fetch.once('error', (err) => {
              console.error('Fetch error in INBOX:', err);
              imap.end();
              resolve();
            });
            fetch.once('end', () => {
              if (pendingOperations === 0) {
                setTimeout(() => {
                  console.log('Finished processing INBOX');
                  imap.end();
                  resolve();
                }, 2000);
              }
            });
          });
        });
      } catch (error) {
        console.error('Error in checkEmails:', error);
        imap.end();
        resolve();
      }
    });
    imap.once('error', (err) => {
      console.error('IMAP connection error:', err);
      reject(err);
    });
    imap.once('end', () => {
      console.log('IMAP connection ended');
      resolve();
    });
    imap.connect();
  });
}

// Exported function for serverless/cloud function use
exports.emailWatcher = async (req, res) => {
  try {
    console.log('Email watcher function triggered');
    await checkEmails();
    res.status(200).send('Email check completed successfully');
  } catch (error) {
    console.error('Function error:', error);
    res.status(500).send(`Error: ${error.message}`);
  }
};
