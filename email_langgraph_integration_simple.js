const nodemailer = require('nodemailer');
const Imap = require('imap');
const { simpleParser } = require('mailparser');
const axios = require('axios');
const { getFirestore, doc, getDoc, setDoc } = require('firebase/firestore');
const { initializeApp } = require('firebase/app');
const { PubSub } = require('@google-cloud/pubsub');
require('dotenv').config();

// Initialize Firebase/Firestore
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
} else {
  console.warn('⚠️ Firebase credentials not found - using file-based storage');
}

// Configuration
const GMAIL_USER = process.env.GMAIL_USER;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;
const EMAIL_FUNCTION_URL = process.env.EMAIL_FUNCTION_URL;
const POLL_INTERVAL = 10000; // 10 seconds

console.log('Gmail User:', GMAIL_USER);
console.log('App Password length:', GMAIL_APP_PASSWORD ? GMAIL_APP_PASSWORD.length : 0);
console.log('Email Function URL:', EMAIL_FUNCTION_URL);

// Simple in-memory tracking
const processedEmails = new Set();
const pubsub = new PubSub();
const topicName = 'incoming-messages';

// Simple state management
async function loadTaskAgentState(customerEmail) {
  if (db) {
    try {
      const docRef = doc(db, 'taskAgent1', customerEmail);
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        return docSnap.data();
      }
    } catch (error) {
      console.error('Error loading state from Firestore:', error.message);
    }
  }
  
  return {
    customerEmail: customerEmail,
    tasks: {},
    createdAt: new Date().toISOString(),
    lastUpdated: new Date().toISOString()
  };
}

async function saveTaskAgentState(customerEmail, state) {
  if (db) {
    try {
      const docRef = doc(db, 'taskAgent1', customerEmail);
      await setDoc(docRef, state);
      console.log(`✅ Saved state to Firestore for ${customerEmail}`);
    } catch (error) {
      console.error('Error saving state to Firestore:', error.message);
    }
  }
}

// Simple email sending
async function sendEmailViaGCP(to, subject, body) {
  try {
    const response = await axios.post(EMAIL_FUNCTION_URL, {
      to: to,
      subject: subject,
      body: body
    }, {
      headers: { 'Content-Type': 'application/json' }
    });
    
    console.log(`✅ Email sent successfully to ${to}`);
    return true;
  } catch (error) {
    console.error('❌ Failed to send email:', error.message);
    return false;
  }
}

// Simple IMAP connection
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

// Process a single email
async function processEmail(imap, message, folderName) {
  return new Promise((resolve, reject) => {
    const fetch = imap.fetch(message, { bodies: '' });
    
    fetch.on('message', (msg, seqno) => {
      msg.on('body', async (stream, info) => {
        try {
          const parsed = await simpleParser(stream);
          
          // Extract email details
          const messageId = parsed.messageId;
          const from = parsed.from?.text || '';
          const subject = parsed.subject || '';
          const text = parsed.text || '';
          const date = parsed.date;
          
          console.log(`=== EMAIL PROCESSING DEBUG ===`);
          console.log(`Message ID: ${messageId}`);
          console.log(`Date: ${date}`);
          console.log(`From: ${from}`);
          console.log(`Subject: ${subject}`);
          console.log(`Folder: ${folderName}`);
          console.log(`Already processed: ${processedEmails.has(messageId)}`);
          console.log(`================================`);
          
          // Skip if already processed
          if (processedEmails.has(messageId)) {
            console.log(`🚫 Email already processed: ${messageId}`);
            resolve();
            return;
          }
          
          // Check if this is a relevant email
          const isPrizmEmail = subject.includes('Prizm Task Question') || 
                              subject.includes('AI Assistant Response') ||
                              subject.includes('Re: Prizm');
          
          if (!isPrizmEmail) {
            console.log(`📧 Skipping non-Prizm email: ${subject}`);
            resolve();
            return;
          }
          
          // Extract user email
          const userEmailMatch = from.match(/<(.+?)>/);
          const userEmail = userEmailMatch ? userEmailMatch[1] : from;
          
          if (!userEmail.includes('@')) {
            console.log(`❌ Invalid email address: ${userEmail}`);
            resolve();
            return;
          }
          
          console.log(`✅ Marked email as processed: ${messageId}`);
          processedEmails.add(messageId);
          
          console.log(`Processing reply from: ${userEmail}`);
          console.log(`User response: ${text.substring(0, 100)}...`);
          
          // Load current state
          const taskAgentState = await loadTaskAgentState(userEmail);
          
          // Initialize task if needed
          const taskTitle = 'Prizm Task Question';
          if (!taskAgentState.tasks[taskTitle]) {
            taskAgentState.tasks[taskTitle] = {
              taskStartConvo: [],
              status: 'active',
              createdAt: new Date().toISOString(),
              lastUpdated: new Date().toISOString(),
              taskInfo: {
                title: taskTitle,
                description: 'Task initiated via email',
                priority: 'medium',
                assignedAgent: 'taskAgent1'
              }
            };
          }
          
          // Save state
          await saveTaskAgentState(userEmail, taskAgentState);
          
          // Publish to Pub/Sub
          const messageData = {
            userEmail: userEmail,
            message: text,
            taskTitle: taskTitle,
            timestamp: new Date().toISOString()
          };
          
          const messageBuffer = Buffer.from(JSON.stringify(messageData));
          const messageId_pubsub = await pubsub.topic(topicName).publish(messageBuffer);
          console.log(`✅ Message ${messageId_pubsub} published to topic ${topicName}.`);
          
          console.log(`Processed email reply for: ${userEmail}`);
          console.log(`Total processed emails: ${processedEmails.size}`);
          
          resolve();
          
        } catch (error) {
          console.error('Error processing email:', error);
          reject(error);
        }
      });
    });
    
    fetch.on('error', (err) => {
      console.error('Fetch error:', err);
      reject(err);
    });
    
    fetch.on('end', () => {
      resolve();
    });
  });
}

// Main email checking function
async function checkEmails() {
  const imap = createImapConnection();
  
  return new Promise((resolve, reject) => {
    imap.once('ready', async () => {
      try {
        console.log('Searching in INBOX folder');
        
        imap.openBox('INBOX', false, (err, box) => {
          if (err) {
            console.error('Error opening INBOX:', err);
            reject(err);
            return;
          }
          
          // Search for unread emails
          const searchCriteria = ['UNSEEN'];
          console.log('Search criteria:', searchCriteria);
          
          imap.search(searchCriteria, (err, results) => {
            if (err) {
              console.error('Search error:', err);
              reject(err);
              return;
            }
            
            if (results.length === 0) {
              console.log('No new unread emails found in INBOX');
              imap.end();
              resolve();
              return;
            }
            
            console.log(`Found ${results.length} new unread emails in INBOX`);
            
            // Process emails sequentially
            let processedCount = 0;
            
            const processNext = async (index) => {
              if (index >= results.length) {
                console.log(`Done processing ${processedCount} emails`);
                imap.end();
                resolve();
                return;
              }
              
              try {
                await processEmail(imap, results[index], 'INBOX');
                processedCount++;
                processNext(index + 1);
              } catch (error) {
                console.error(`Error processing email ${index}:`, error);
                processNext(index + 1); // Continue with next email
              }
            };
            
            processNext(0);
          });
        });
        
      } catch (error) {
        console.error('Error in checkEmails:', error);
        reject(error);
      }
    });
    
    imap.once('error', (err) => {
      console.error('IMAP connection error:', err);
      reject(err);
    });
    
    imap.once('end', () => {
      console.log('IMAP connection ended');
    });
    
    imap.connect();
  });
}

// Main polling function
async function startEmailPolling() {
  console.log('Starting to watch for new Prizm email replies...');
  console.log('Email integration is running. Press Ctrl+C to stop.');
  
  while (true) {
    try {
      await checkEmails();
    } catch (error) {
      console.error('Error in email polling cycle:', error);
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
  }
}

// Start the application
async function main() {
  try {
    await startEmailPolling();
  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down gracefully...');
  process.exit(0);
});

// Start the application
main().catch(console.error); 