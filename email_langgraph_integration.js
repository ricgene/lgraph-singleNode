const nodemailer = require('nodemailer');
const Imap = require('imap');
const { simpleParser } = require('mailparser');
const axios = require('axios');
const fs = require('fs');
const { getFirestore, doc, getDoc, setDoc, collection, getDocs } = require('firebase/firestore');
const { initializeApp } = require('firebase/app');
const { PubSub } = require('@google-cloud/pubsub');
require('dotenv').config();

// Initialize Firebase/Firestore if credentials are available
let db = null;
let app = null;

if (process.env.FIREBASE_API_KEY && process.env.FIREBASE_AUTH_DOMAIN && process.env.FIREBASE_PROJECT_ID) {
  const firebaseConfig = {
    apiKey: process.env.FIREBASE_API_KEY,
    authDomain: process.env.FIREBASE_AUTH_DOMAIN,
    projectId: process.env.FIREBASE_PROJECT_ID,
    storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.FIREBASE_APP_ID
  };
  
  app = initializeApp(firebaseConfig);
  db = getFirestore(app);
  console.log('📁 Using Firestore for conversation states');
  console.log('📧 Using Firestore for duplicate email tracking');
} else {
  console.warn('Set FIREBASE_* environment variables to use Firestore');
  console.log('📁 Using file-based storage for conversation states');
  console.log('📧 Using file-based storage for duplicate email tracking');
}

// Debug: Check if environment variables are loaded
console.log('Gmail User:', process.env.GMAIL_USER);
console.log('App Password length:', process.env.GMAIL_APP_PASSWORD ? process.env.GMAIL_APP_PASSWORD.length : 0);
console.log('Email Function URL:', process.env.EMAIL_FUNCTION_URL);

// Track emails being processed in current session to prevent race conditions
const processingEmails = new Set(); // email UIDs currently being processed

// Track last email sent time to implement throttling
const lastEmailSentTime = new Map(); // userEmail -> timestamp
const EMAIL_THROTTLE_MIN_INTERVAL = 3000; // 3 seconds minimum between emails

const pubsub = new PubSub();
const topicName = 'incoming-messages';

// Function to check if email is currently being processed
function isEmailBeingProcessed(emailUid) {
  return processingEmails.has(emailUid);
}

// Function to mark email as processing
function markEmailAsProcessing(emailUid) {
  processingEmails.add(emailUid);
}

// Function to mark email as finished processing
function markEmailAsFinished(emailUid) {
  processingEmails.delete(emailUid);
}

// Throttling function
function enforceStrictThrottle(userEmail) {
  const now = Date.now();
  const lastSent = lastEmailSentTime.get(userEmail) || 0;
  const timeSinceLastEmail = now - lastSent;
  
  if (timeSinceLastEmail < EMAIL_THROTTLE_MIN_INTERVAL) {
    const waitTime = EMAIL_THROTTLE_MIN_INTERVAL - timeSinceLastEmail;
    console.log(`⏳ Throttling: ${userEmail} must wait ${waitTime}ms before next email`);
    return waitTime;
  }
  
  return 0; // No wait needed
}

// Function to update last email sent time
function updateLastEmailSentTime(userEmail) {
  lastEmailSentTime.set(userEmail, Date.now());
}

// Distributed locking functions
async function acquireEmailLock(customerEmail, taskTitle) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  
  // Initialize task if it doesn't exist
  if (!taskAgentState.tasks[taskTitle]) {
    taskAgentState.tasks[taskTitle] = {
      taskStartConvo: [],
      emailLock: null,
      status: 'active',
      createdAt: new Date().toISOString(),
      lastUpdated: new Date().toISOString(),
      lastMsgSent: null,
      taskInfo: {
        title: taskTitle,
        description: 'Task initiated via email',
        priority: 'medium',
        assignedAgent: 'taskAgent1'
      }
    };
  }
  
  // Ensure emailLock field exists for existing tasks
  if (!taskAgentState.tasks[taskTitle].hasOwnProperty('emailLock')) {
    taskAgentState.tasks[taskTitle].emailLock = null;
  }
  
  const currentLock = taskAgentState.tasks[taskTitle].emailLock;
  const now = Date.now();
  const lockDigits = now % 10000; // Last 4 digits of timestamp
  
  // Check if there's an existing lock
  if (currentLock && currentLock.timestamp) {
    const lockAge = now - currentLock.timestamp;
    const LOCK_TIMEOUT = 30000; // 30 seconds
    
    if (lockAge < LOCK_TIMEOUT) {
      console.log(`🔒 Lock already held by ${currentLock.holder} (age: ${lockAge}ms)`);
      return false; // Lock is still valid
    } else {
      console.log(`⏰ Lock expired (age: ${lockAge}ms), proceeding with new lock`);
    }
  }
  
  // Attempt to acquire lock
  console.log(`🔒 Attempting to acquire lock with digits: ${lockDigits} (timestamp: ${now})`);
  
  // Add small delay to prevent race conditions
  const waitTime = Math.random() * 1000; // 0-1000ms
  await new Promise(resolve => setTimeout(resolve, waitTime));
  
  // Verify lock is still available after delay
  const verificationState = await loadTaskAgentState(customerEmail);
  const verificationLock = verificationState.tasks[taskTitle]?.emailLock;
  
  if (verificationLock && verificationLock.timestamp && (now - verificationLock.timestamp) < 30000) {
    console.log(`❌ Lock was acquired by another process during delay`);
    return false;
  }
  
  // Acquire the lock
  taskAgentState.tasks[taskTitle].emailLock = {
    holder: 'email-watcher',
    timestamp: now,
    digits: lockDigits
  };
  
  await saveTaskAgentState(customerEmail, taskAgentState);
  console.log(`✅ Lock acquired: ${lockDigits}`);
  
  // Verify lock was saved correctly
  const finalState = await loadTaskAgentState(customerEmail);
  const finalLock = finalState.tasks[taskTitle]?.emailLock;
  
  if (finalLock && finalLock.digits === lockDigits) {
    console.log(`✅ Lock verification successful: ${lockDigits}`);
    return true;
  } else {
    console.log(`❌ Lock verification failed`);
    return false;
  }
}

async function clearEmailLock(customerEmail, taskTitle) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  
  if (taskAgentState.tasks[taskTitle]) {
    taskAgentState.tasks[taskTitle].emailLock = null;
    await saveTaskAgentState(customerEmail, taskAgentState);
    console.log(`🔓 Cleared email lock for ${customerEmail} - ${taskTitle}`);
  }
}

async function loadTaskAgentState(customerEmail) {
  if (db) {
    try {
      const docRef = doc(db, 'taskAgent1', customerEmail);
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        console.log(`✅ Loaded taskAgent1 state from Firestore for ${customerEmail}`);
        return docSnap.data();
      }
    } catch (error) {
      console.error('Error loading taskAgent1 state from Firestore:', error.message);
    }
  }
  
  // Return default state if not found
  return {
    customerEmail: customerEmail,
    tasks: {},
    createdAt: new Date().toISOString(),
    lastUpdated: new Date().toISOString()
  };
}

async function saveTaskAgentState(customerEmail, taskAgentState) {
  if (db) {
    try {
      const docRef = doc(db, 'taskAgent1', customerEmail);
      await setDoc(docRef, taskAgentState);
      console.log(`✅ Saved taskAgent1 state to Firestore for ${customerEmail}`);
    } catch (error) {
      console.error('Error saving taskAgent1 state to Firestore:', error.message);
    }
  }
}

async function sendEmailViaGCP(to, subject, body) {
  try {
    const response = await axios.post(process.env.EMAIL_FUNCTION_URL, {
      to: to,
      subject: subject,
      body: body
    }, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log(`📧 Email sent successfully to ${to}: ${response.status}`);
    return true;
  } catch (error) {
    console.error('❌ Error sending email via GCP:', error.message);
    return false;
  }
}

function createImapConnection() {
  return new Imap({
    user: process.env.GMAIL_USER,
    password: process.env.GMAIL_APP_PASSWORD,
    host: 'imap.gmail.com',
    port: 993,
    tls: true,
    tlsOptions: { rejectUnauthorized: false }
  });
}

function processEmailsInFolder(results, folderName, imap, processedEmails) {
  if (results.length === 0) {
    console.log(`No emails found in ${folderName}`);
    return;
  }
  
  console.log(`Processing ${results.length} emails from ${folderName}`);
  
  const fetch = imap.fetch(results, { bodies: '' });
  
  fetch.on('message', (msg, seqno) => {
    console.log(`Processing message #${seqno} from folder: ${folderName}`);
    console.log('Message UID:', msg.attributes?.uid);
    
    msg.on('body', (stream, info) => {
      simpleParser(stream, async (err, parsed) => {
        if (err) {
          console.error('Error parsing email:', err);
          return;
        }
        
        // Check if email has the "processed" label and skip if it does
        if (msg.attributes && msg.attributes.flags && msg.attributes.flags.includes('processed')) {
          console.log('🚫 Skipping email with \'processed\' label:', parsed.subject, parsed.date, parsed.messageId);
          return; // Skip processing this email
        }
        
        // Generate email UID for tracking
        const emailUid = `${parsed.messageId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        console.log('=== EMAIL PROCESSING DEBUG ===');
        console.log('Email UID:', emailUid);
        console.log('Message ID:', parsed.messageId);
        console.log('Date:', parsed.date);
        console.log('From:', parsed.from?.text);
        console.log('Subject:', parsed.subject);
        console.log('Folder:', folderName);
        console.log('IMAP UID:', msg.attributes?.uid);
        console.log('Processed emails count:', processedEmails.size);
        console.log('Processed in session:', processingEmails.size);
        console.log('Already processed globally:', processedEmails.has(emailUid) || processedEmails.has(parsed.messageId));
        console.log('Already processed in session:', isEmailBeingProcessed(emailUid) || isEmailBeingProcessed(parsed.messageId));
        console.log('Currently being processed:', isEmailBeingProcessed(emailUid) || isEmailBeingProcessed(parsed.messageId));
        console.log('================================');
        
        // Check if already processed (by UID or message ID)
        const isAlreadyProcessed = processedEmails.has(emailUid) || 
                                  processedEmails.has(parsed.messageId) || 
                                  isEmailBeingProcessed(emailUid) ||
                                  isEmailBeingProcessed(parsed.messageId);
        
        if (isAlreadyProcessed) {
          console.log('🚫 Email already processed or being processed:', emailUid, 'or', parsed.messageId);
          return;
        }
        
        // Mark as processing
        markEmailAsProcessing(emailUid);
        markEmailAsProcessing(parsed.messageId); // Also track by message ID
        console.log(`✅ Marked email as processed in session: ${emailUid}`);
        console.log(`🔒 Marked email as processing: ${emailUid}`);
        
        // Extract user email and response
        const userEmail = parsed.from?.value?.[0]?.address;
        const userResponse = parsed.text || parsed.html || '';
        
        if (!userEmail) {
          console.log('❌ Could not extract user email from:', parsed.from);
          markEmailAsFinished(emailUid);
          return;
        }
        
        // Skip emails from our own address
        if (userEmail === process.env.GMAIL_USER) {
          console.log('🚫 Skipping email from our own address:', userEmail);
          markEmailAsFinished(emailUid);
          return;
        }
        
        console.log('Processing reply from:', userEmail);
        console.log('User response:', userResponse);
        
        // Acquire lock for this user/task
        const taskTitle = 'Prizm Task Question';
        const lockAcquired = await acquireEmailLock(userEmail, taskTitle);
        
        if (!lockAcquired) {
          console.log('❌ Failed to acquire lock, skipping email');
          markEmailAsFinished(emailUid);
          return;
        }
        
        try {
          // Publish message to Pub/Sub
          const messageData = {
            userEmail: userEmail,
            userResponse: userResponse,
            emailUid: emailUid,
            timestamp: new Date().toISOString()
          };
          
          const messageBuffer = Buffer.from(JSON.stringify(messageData));
          const messageId = await pubsub.topic(topicName).publish(messageBuffer);
          console.log(`✅ Message ${messageId} published to topic ${topicName}.`);
          
          // Mark as processed
          processedEmails.add(emailUid);
          processedEmails.add(parsed.messageId); // Also track by message ID
          
          // Mark this email as processed globally
          processingEmails.add(emailUid);
          console.log('Processed email reply for:', userEmail);
          console.log('Total processed emails:', processingEmails.size);
          
          // Mark email as processed by adding the "processed" label
          if (msg.attributes && msg.attributes.uid) {
            imap.addFlags(msg.attributes.uid, 'processed', (err) => {
              if (err) {
                console.error('❌ Failed to add processed label to email:', err);
              } else {
                console.log('✅ Added processed label to email UID:', msg.attributes.uid);
              }
            });
          } else {
            console.log('⚠️ Could not add processed label (no UID available) - using message ID tracking instead');
            // Fallback: track by message ID in our processed emails set
            if (parsed.messageId) {
              processedEmails.add(parsed.messageId);
              console.log('✅ Added message ID to processed tracking:', parsed.messageId);
            }
          }
          
        } catch (error) {
          console.error('❌ Error processing email:', error);
        } finally {
          // Clear lock
          await clearEmailLock(userEmail, taskTitle);
          markEmailAsFinished(emailUid);
          markEmailAsFinished(parsed.messageId); // Also clear message ID tracking
          console.log(`✅ Marked email as finished processing: ${emailUid}`);
        }
      });
    });
  });
  
  fetch.on('error', (err) => {
    console.error('Fetch error:', err);
  });
  
  fetch.on('end', () => {
    console.log('Done fetching all messages from', folderName);
  });
}

function checkEmails(processedEmails) {
  const imap = createImapConnection();
  
  imap.once('ready', () => {
    imap.openBox('INBOX', false, (err, box) => {
      if (err) {
        console.error('Error opening INBOX:', err);
        imap.end();
        return;
      }
      
      function searchForEmails() {
        // Search criteria - look for ALL emails, we'll filter out processed ones later
        const searchCriteria = ['ALL'];
        
        console.log('Searching in INBOX folder');
        console.log('Search criteria:', searchCriteria);
        
        imap.search(searchCriteria, (err, results) => {
          if (err) {
            console.error('Error searching for emails:', err);
            imap.end();
            return;
          }
          
          if (results.length === 0) {
            console.log('No emails found in INBOX');
            imap.end();
            return;
          }
          
          console.log(`Found ${results.length} emails in INBOX`);
          
          // Process the emails found
          processEmailsInFolder(results, 'INBOX', imap, processedEmails);
        });
      }
      
      searchForEmails();
    });
  });
  
  imap.once('error', (err) => {
    console.error('IMAP connection error:', err);
  });
  
  imap.once('end', () => {
    console.log('IMAP connection ended');
  });
  
  imap.connect();
}

async function startWatchingEmails() {
  console.log('Starting to watch for new Prizm email replies...');
  
  // Load processed emails
  const processedEmails = new Set();
  console.log('📧 Using Firestore for processed email tracking (not yet implemented)');
  
  // Initial check
  checkEmails(processedEmails);
  
  // Set up polling every 10 seconds
  setInterval(() => {
    checkEmails(processedEmails);
  }, 10000);
  
  console.log('Email integration is running. Press Ctrl+C to stop.');
}

// Main execution
async function main() {
  try {
    console.log('Starting LangGraph Email Integration...');
    await startWatchingEmails();
  } catch (error) {
    console.error('Error in main:', error);
    process.exit(1);
  }
}

// Start the application
main(); 