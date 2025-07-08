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
  
  console.log('Raw email content:', content);
  
  // Initialize task data structure
  const taskData = {
    custemail: userEmail,
    source: 'email',
    emailSubject: parsed.subject,
    emailDate: parsed.date,
    rawContent: content
  };
  
  // Custom parser for this specific format
  // The content looks like: "field":value, "field":value
  const lines = content.split('\n');
  
  for (const line of lines) {
    const trimmedLine = line.trim();
    if (trimmedLine.includes('":')) {
      // Extract field name and value
      const colonIndex = trimmedLine.indexOf('":');
      if (colonIndex > 0) {
        const fieldName = trimmedLine.substring(1, colonIndex); // Remove leading quote
        let value = trimmedLine.substring(colonIndex + 2); // Skip ":"
        
        // Remove trailing comma and quotes
        value = value.replace(/,$/, '').replace(/^"|"$/g, '');
        
        // Clean up the value
        value = value.trim();
        
        // Map field names to expected format
        const fieldMapping = {
          'custemail': 'custemail',
          'phone': 'phone',
          'Task': 'Task',
          'description': 'description',
          'Category': 'Category',
          'DueDate': 'DueDate',
          'Posted': 'Posted',
          'FullAddress': 'FullAddress',
          'Task Budget': 'Task Budget',
          'State': 'State',
          'vendors': 'vendors'
        };
        
        const mappedField = fieldMapping[fieldName];
        if (mappedField && value) {
          taskData[mappedField] = value;
          console.log(`✅ Extracted ${mappedField}: ${value}`);
        }
      }
    }
  }
  
  // Set default values if not found
  if (!taskData['Customer Name'] && taskData.custemail) {
    taskData['Customer Name'] = taskData.custemail.split('@')[0];
  }
  
  if (!taskData['Task'] && parsed.subject) {
    taskData['Task'] = parsed.subject;
  }
  
  // Set description from email content
  taskData.description = content.substring(0, 500); // First 500 chars as description
  
  console.log('📋 Final extracted task data:', JSON.stringify(taskData, null, 2));
  
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
      return { shouldDelete: false };
    }

    // Firestore deduplication with logging
    if (await isProcessed(messageId)) {
      console.log(`🚫 Already processed: ${messageId}`);
      return { shouldDelete: false };
    }

    // Skip system-generated emails but allow task creation emails from same account
    if (from === GMAIL_USER) {
      // Check if this is a system-generated email (like responses we sent)
      const isSystemEmail = subject && (
        subject.toLowerCase().includes('re:') || 
        subject.toLowerCase().includes('response') ||
        subject.toLowerCase().includes('reply') ||
        text.includes('I\'m your AI assistant') ||
        text.includes('LangGraph') ||
        text.includes('conversation')
      );
      
      if (isSystemEmail) {
        console.log('🚫 Skipping system-generated email from our own address:', from, 'Subject:', subject);
        return { shouldDelete: false };
      } else {
        console.log('✅ Processing task email from monitored account:', from, 'Subject:', subject);
      }
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
        return { shouldDelete: false }; // Don't process or delete non-task emails
      }
    }
    
    if (processingSuccess) {
      // Mark as processed in Firestore
      await markProcessed(messageId, { from, subject, taskCreation: isTaskCreationEmail });
      
      // Return result indicating email should be deleted
      console.log(`✅ Email processed successfully - will be deleted`);
      return { shouldDelete: true, uid, messageId };
    } else {
      console.log(`❌ Email processing failed - will not be deleted`);
      return { shouldDelete: false };
    }
    
  } catch (error) {
    console.error('❌ Error processing email:', error);
    return { shouldDelete: false };
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
    let emailsToDelete = []; // Track emails that need deletion

    imap.once('ready', async () => {
      console.log('IMAP connection ready');
      try {
        await listFolders(imap);
        
        // Check both INBOX and All Mail folders
        const foldersToCheck = ['INBOX', '[Gmail]/All Mail'];
        
        for (const folderName of foldersToCheck) {
          console.log(`Checking folder: ${folderName}`);
          
          try {
            await new Promise((folderResolve, folderReject) => {
              imap.openBox(folderName, false, (err, box) => {
                if (err) {
                  console.error(`Error opening ${folderName}:`, err);
                  folderResolve();
                  return;
                }
                
                if (box.messages.total === 0) {
                  console.log(`No emails found in ${folderName}`);
                  folderResolve();
                  return;
                }
                
                console.log(`Found ${box.messages.total} emails in ${folderName}`);
                imap.search(['ALL'], (err, results) => {
                  if (err) {
                    console.error(`Search error in ${folderName}:`, err);
                    folderResolve();
                    return;
                  }
                  
                  const recentEmails = results.slice(-10);
                  console.log(`Processing ${recentEmails.length} most recent emails from ${folderName}`);
                  
                  if (recentEmails.length === 0) {
                    folderResolve();
                    return;
                  }
                  
                  const fetch = imap.fetch(recentEmails, { bodies: '', struct: true, extensions: true });
                  
                  fetch.on('message', (msg, seqno) => {
                    let uid = null;
                    msg.on('attributes', (attrs) => {
                      uid = attrs.uid;
                    });
                    msg.on('body', (stream, info) => {
                      pendingOperations++;
                      processEmail(imap, stream, { uid: uid, seqno: seqno, folder: folderName }).then((result) => {
                        // Track emails that were successfully processed and need deletion
                        if (result && result.shouldDelete && uid) {
                          emailsToDelete.push({ uid, folder: folderName });
                          console.log(`📝 Queued email UID ${uid} from ${folderName} for deletion`);
                        }
                      }).catch((error) => {
                        console.error(`❌ Error processing email ${seqno} from ${folderName}:`, error);
                      }).finally(() => {
                        pendingOperations--;
                        if (pendingOperations === 0) {
                          // Delete all queued emails before closing connection
                          deleteQueuedEmails(imap, emailsToDelete).then(() => {
                            console.log(`Finished processing ${folderName}`);
                            folderResolve();
                          }).catch((error) => {
                            console.error('Error during final deletion:', error);
                            folderResolve();
                          });
                        }
                      });
                    });
                  });
                  
                  fetch.once('error', (err) => {
                    console.error(`Fetch error in ${folderName}:`, err);
                    folderResolve();
                  });
                  
                  fetch.once('end', () => {
                    if (pendingOperations === 0) {
                      // Delete all queued emails before closing connection
                      deleteQueuedEmails(imap, emailsToDelete).then(() => {
                        console.log(`Finished processing ${folderName}`);
                        folderResolve();
                      }).catch((error) => {
                        console.error('Error during final deletion:', error);
                        folderResolve();
                      });
                    }
                  });
                });
              });
            });
          } catch (folderError) {
            console.error(`Error processing folder ${folderName}:`, folderError);
          }
        }
        
        console.log('Finished processing all folders');
        imap.end();
        resolve();
        
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

// Helper function to delete queued emails
async function deleteQueuedEmails(imap, emailsToDelete) {
  if (emailsToDelete.length === 0) {
    console.log('ℹ️ No emails queued for deletion');
    return;
  }
  
  console.log(`🗑️ Deleting ${emailsToDelete.length} processed emails...`);
  
  try {
    // Group emails by folder
    const emailsByFolder = {};
    emailsToDelete.forEach(email => {
      if (!emailsByFolder[email.folder]) {
        emailsByFolder[email.folder] = [];
      }
      emailsByFolder[email.folder].push(email.uid);
    });
    
    // Delete emails from each folder
    for (const [folder, uids] of Object.entries(emailsByFolder)) {
      console.log(`🗑️ Processing deletions for folder: ${folder}`);
      
      // Open the folder
      await new Promise((resolve, reject) => {
        imap.openBox(folder, false, (err) => {
          if (err) {
            console.error(`❌ Error opening ${folder} for deletion:`, err);
            resolve();
          } else {
            resolve();
          }
        });
      });
      
      // Mark emails as deleted
      for (const uid of uids) {
        await new Promise((resolve, reject) => {
          imap.addFlags(uid, '\\Deleted', (err) => {
            if (err) {
              console.error(`❌ Failed to mark email UID ${uid} in ${folder} for deletion:`, err);
              resolve(); // Continue with other emails
            } else {
              console.log(`✅ Marked email UID ${uid} in ${folder} for deletion`);
              resolve();
            }
          });
        });
      }
      
      // Expunge deleted emails from this folder
      await new Promise((resolve, reject) => {
        imap.expunge((err) => {
          if (err) {
            console.error(`❌ Failed to expunge deleted emails from ${folder}:`, err);
            resolve(); // Continue with other folders
          } else {
            console.log(`🗑️ Successfully deleted ${uids.length} emails from ${folder}`);
            resolve();
          }
        });
      });
    }
    
    console.log(`✅ Completed deletion of ${emailsToDelete.length} emails from all folders`);
    
  } catch (error) {
    console.error('❌ Error during batch deletion:', error);
    throw error;
  }
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
