const nodemailer = require('nodemailer');
const Imap = require('imap');
const { simpleParser } = require('mailparser');
const axios = require('axios');
const fs = require('fs');
const { getFirestore, doc, getDoc, setDoc, collection, getDocs } = require('firebase/firestore');
const { initializeApp } = require('firebase/app');
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

// File paths for persistent storage
const CONVERSATION_STATES_FILE = 'conversation_states.json';
const PROCESSED_EMAILS_FILE = 'processed_emails.json';

// Track recent user activity to prevent duplicate processing
const recentUserActivity = new Map(); // userEmail -> timestamp
const DEDUPLICATION_WINDOW = 60000; // 60 seconds in milliseconds

// Track emails being processed in current session to prevent race conditions
const processingEmails = new Set(); // email UIDs currently being processed

// Track last email sent time to implement throttling
const lastEmailSentTime = new Map(); // userEmail -> timestamp
const EMAIL_THROTTLE_MIN_INTERVAL = 3000; // 3 seconds minimum between emails

// Track processed email content with timestamps (in-memory only)
const processedEmailContent = new Map(); // userEmail -> { contentHash: timestamp }

const watcherStartTime = Date.now(); // Record watcher start time

// Function to check if user has been processed recently
function isUserRecentlyProcessed(userEmail) {
  const lastProcessed = recentUserActivity.get(userEmail);
  if (!lastProcessed) return false;
  
  const timeSinceLastProcessed = Date.now() - lastProcessed;
  const MIN_INTERVAL = 5000; // 5 seconds minimum between processing same user
  
  return timeSinceLastProcessed < MIN_INTERVAL;
}

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

// Function to load conversation states from Firestore or file
async function loadConversationStates() {
  if (db) {
    try {
      // Load all conversation states from Firestore
      const statesRef = collection(db, 'conversation_states');
      const snapshot = await getDocs(statesRef);
      const states = {};
      snapshot.forEach(doc => {
        states[doc.id] = doc.data();
      });
      return states;
    } catch (error) {
      console.error('Error loading conversation states from Firestore:', error.message);
      return {};
    }
  } else {
    // Fallback to file-based storage
    try {
      const data = fs.readFileSync('simple_conversation_states.json', 'utf8');
      return JSON.parse(data);
    } catch (error) {
      return {};
    }
  }
}

// Function to save conversation state to Firestore or file
async function saveConversationState(userEmail, state) {
  if (db) {
    try {
      // Save to Firestore
      const docRef = doc(db, 'conversation_states', userEmail);
      await setDoc(docRef, state);
      console.log(`✅ Saved conversation state to Firestore for ${userEmail}`);
    } catch (error) {
      console.error('Error saving conversation state to Firestore:', error.message);
    }
  } else {
    // Fallback to file-based storage
    try {
      const states = await loadConversationStates();
      states[userEmail] = state;
      fs.writeFileSync('simple_conversation_states.json', JSON.stringify(states, null, 2));
    } catch (error) {
      console.error('Error saving conversation state to file:', error.message);
    }
  }
}

// Function to load conversation state for a specific user from Firestore or file
async function loadConversationState(userEmail) {
  if (db) {
    try {
      // Load from Firestore
      const docRef = doc(db, 'conversation_states', userEmail);
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        console.log(`✅ Loaded conversation state from Firestore for ${userEmail}`);
        return docSnap.data();
      }
      return null;
    } catch (error) {
      console.error('Error loading conversation state from Firestore:', error.message);
      return null;
    }
  } else {
    // Fallback to file-based storage
    try {
      const states = await loadConversationStates();
      return states[userEmail] || null;
    } catch (error) {
      return null;
    }
  }
}

// Function to load processed email IDs from Firestore or file
function loadProcessedEmails() {
  if (db) {
    try {
      // Load from Firestore - for now, return empty set since we need to implement this
      // In a real implementation, you'd store processed email IDs in Firestore
      console.log('📧 Using Firestore for processed email tracking (not yet implemented)');
      return new Set();
    } catch (error) {
      console.error('Error loading processed emails from Firestore:', error.message);
      return new Set();
    }
  } else {
    // Fallback to file-based storage
    try {
      if (fs.existsSync(PROCESSED_EMAILS_FILE)) {
        const data = fs.readFileSync(PROCESSED_EMAILS_FILE, 'utf8');
        const emailIds = JSON.parse(data);
        console.log(`📧 Loaded ${emailIds.length} previously processed email IDs from file`);
        return new Set(emailIds);
      }
    } catch (error) {
      console.error('Error loading processed emails from file:', error.message);
    }
    return new Set();
  }
}

// Function to save processed email IDs to Firestore or file
function saveProcessedEmails(processedEmails) {
  if (db) {
    try {
      // Save to Firestore - for now, just log since we need to implement this
      // In a real implementation, you'd store processed email IDs in Firestore
      console.log(`📧 Would save ${processedEmails.size} processed email IDs to Firestore (not yet implemented)`);
    } catch (error) {
      console.error('Error saving processed emails to Firestore:', error.message);
    }
  } else {
    // Fallback to file-based storage
    try {
      const emailIds = Array.from(processedEmails);
      
      // Keep only the last 1000 processed emails to prevent file from growing too large
      const maxEmails = 1000;
      const recentEmails = emailIds.slice(-maxEmails);
      
      fs.writeFileSync(PROCESSED_EMAILS_FILE, JSON.stringify(recentEmails, null, 2));
      console.log(`📧 Saved ${recentEmails.length} processed email IDs to file (kept last ${maxEmails})`);
    } catch (error) {
      console.error('Error saving processed emails to file:', error.message);
    }
  }
}

// Create a transporter for sending emails
async function createTransporter() {
  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.GMAIL_USER,
      pass: process.env.GMAIL_APP_PASSWORD
    }
  });
  return transporter;
}

// Create an IMAP connection for receiving emails
function createImapConnection() {
  const imapConfig = {
    user: process.env.GMAIL_USER,
    password: process.env.GMAIL_APP_PASSWORD,
    host: 'imap.gmail.com',
    port: 993,
    tls: true,
    tlsOptions: { rejectUnauthorized: false }
  };

  return new Imap(imapConfig);
}

// Function to send an email via the deployed GCP function
async function sendEmailViaGCP(to, subject, body) {
  try {
    const response = await axios.post(process.env.EMAIL_FUNCTION_URL, {
      to: to,
      subject: subject,
      body: body
    });
    
    // Enhanced logging: log status, headers, and body
    console.log('GCP Email Function Response:');
    console.log('Status:', response.status);
    console.log('Headers:', JSON.stringify(response.headers));
    console.log('Body:', typeof response.data === 'object' ? JSON.stringify(response.data) : response.data);
    
    if (response.status === 200) {
      console.log('Email sent via GCP function:', subject);
      return true;
    } else {
      console.error('Failed to send email via GCP function:', response.status);
      return false;
    }
  } catch (error) {
    if (error.response) {
      // The request was made and the server responded with a status code outside 2xx
      console.error('GCP Email Function Error Response:');
      console.error('Status:', error.response.status);
      console.error('Headers:', JSON.stringify(error.response.headers));
      console.error('Body:', typeof error.response.data === 'object' ? JSON.stringify(error.response.data) : error.response.data);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received from GCP Email Function.');
      console.error(error.request);
    } else {
      // Something happened in setting up the request
      console.error('Error setting up GCP Email Function request:', error.message);
    }
    return false;
  }
}

// Function to call the LangGraph process_message function
async function processUserResponse(userEmail, userResponse, conversationState) {
  try {
    // Call the LangGraph function (this would be your Python function)
    // For now, we'll simulate the response
    const response = await axios.post('http://localhost:8000/process_message', {
      user_input: userResponse,
      previous_state: conversationState,
      user_email: userEmail
    });
    
    return response.data;
  } catch (error) {
    console.error('Error calling LangGraph function:', error.message);
    // Fallback: send a simple acknowledgment
    return {
      question: "Thank you for your response. I'm processing your information.",
      is_complete: false,
      conversation_history: conversationState.conversation_history + "\nUser: " + userResponse
    };
  }
}

// Function to process emails found in a specific folder
function processEmailsInFolder(results, folderName, imap, processedEmails) {
  // Use markSeen to prevent re-processing and include UIDs
  const fetch = imap.fetch(results, { 
    bodies: '',
    markSeen: true,
    struct: true
  });
  
  // Track processed messages in this fetch session
  const processedInSession = new Set();
  
  fetch.on('message', (msg, seqno) => {
    console.log(`Processing message #${seqno} from folder: ${folderName}`);
    
    // Get the UID for this message
    const uid = msg.uid;
    console.log('Message UID:', uid);
    
    msg.on('body', async (stream) => {
      simpleParser(stream, async (err, parsed) => {
        if (err) throw err;
        
        // Use IMAP UID as the primary deduplication key (most reliable)
        // If UID is undefined, fall back to message ID + timestamp
        const emailUid = uid ? uid.toString() : 
          `${parsed.messageId || 'no-message-id'}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        console.log('=== EMAIL PROCESSING DEBUG ===');
        console.log('Email UID:', emailUid);
        console.log('Message ID:', parsed.messageId);
        console.log('Date:', parsed.date);
        console.log('From:', parsed.from?.text);
        console.log('Subject:', parsed.subject);
        console.log('Folder:', folderName);
        console.log('IMAP UID:', uid);
        console.log('Processed emails count:', processingEmails.size);
        console.log('Processed in session:', processedInSession.size);
        console.log('Already processed globally:', processingEmails.has(emailUid));
        console.log('Already processed in session:', processedInSession.has(emailUid));
        console.log('Currently being processed:', isEmailBeingProcessed(emailUid));
        console.log('================================');
        
        // Check if we've already processed this email (global or in this session)
        if (processingEmails.has(emailUid) || processedInSession.has(emailUid)) {
          console.log('Skipping already processed email UID:', emailUid);
          return;
        }
        
        // Check if this email is currently being processed (race condition prevention)
        if (isEmailBeingProcessed(emailUid)) {
          console.log('Skipping email UID currently being processed:', emailUid);
          return;
        }
        
        // Check if email is older than watcher start time
        const emailDate = parsed.date ? new Date(parsed.date).getTime() : 0;
        if (emailDate && emailDate < watcherStartTime) {
          // Move this email to Trash and log it
          if (msg.attributes && msg.attributes.uid) {
            imap.addFlags(msg.attributes.uid, '\\Deleted', (err) => {
              if (err) {
                console.error('❌ Failed to mark old email for deletion:', err);
              } else {
                console.log('🗑️ Deleted old email (before watcher start):', parsed.subject, parsed.date, parsed.messageId);
              }
            });
          } else {
            console.log('🗑️ Skipping deletion of old email (no UID available):', parsed.subject, parsed.date, parsed.messageId);
          }
          return; // Skip processing this email
        }
        
        // Mark as processed in this session immediately
        processedInSession.add(emailUid);
        console.log(`✅ Marked email as processed in session: ${emailUid}`);
        
        // Mark as currently processing to prevent race conditions
        markEmailAsProcessing(emailUid);
        console.log(`🔒 Marked email as processing: ${emailUid}`);
        
        try {
          // Extract user's email address
          const userEmail = parsed.from.text.match(/<(.+)>/)?.[1] || parsed.from.text;
          
          // Skip processing emails from our own address
          if (userEmail === process.env.GMAIL_USER) {
            console.log('Skipping email from our own address:', userEmail);
            return;
          }
          
          // Check if user has been processed recently
          if (isUserRecentlyProcessed(userEmail)) {
            return;
          }
          
          // Extract the user's response from the email body
          // Remove quoted text and email headers to get just the user's response
          let userResponse = parsed.text || parsed.html || '';
          
          // Remove quoted text (lines starting with >)
          userResponse = userResponse.split('\n')
            .filter(line => !line.trim().startsWith('>'))
            .join('\n');
          
          // Remove common email headers and signatures
          userResponse = userResponse.replace(/On .+ wrote:.*$/s, '');
          userResponse = userResponse.replace(/Best regards,.*$/s, '');
          userResponse = userResponse.replace(/Helen.*$/s, '');
          userResponse = userResponse.replace(/Prizm.*$/s, '');
          userResponse = userResponse.replace(/Real Estate Concierge Service.*$/s, '');
          userResponse = userResponse.replace(/Please reply to this email.*$/s, '');
          
          // Remove any remaining quoted text patterns
          userResponse = userResponse.replace(/^>.*$/gm, '');
          userResponse = userResponse.replace(/^On .+ at .+ .+ wrote:$/gm, '');
          
          // Clean up the response - remove extra whitespace and empty lines
          userResponse = userResponse
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .join('\n')
            .trim();
          
          // If the response is empty after cleaning, use a fallback
          if (!userResponse || userResponse.length === 0) {
            userResponse = parsed.text || parsed.html || '';
            // Just take the first few lines as a fallback
            userResponse = userResponse.split('\n').slice(0, 3).join('\n').trim();
          }
          
          console.log('Processing reply from:', userEmail);
          console.log('User response:', userResponse);
          
          // Get existing task conversation from taskAgent1 collection
          const taskTitle = "Prizm Task Question"; // Default task title for email conversations
          
          // Try to acquire email lock to prevent duplicate processing
          const lockAcquired = await acquireEmailLock(userEmail, taskTitle);
          if (!lockAcquired) {
            console.log(`🚫 Failed to acquire lock for ${userEmail} - ${taskTitle}. Another responder is processing this email.`);
            markEmailAsFinished(emailUid);
            return;
          }
          
          console.log(`✅ Successfully acquired lock (${lockAcquired}) for ${userEmail} - ${taskTitle}`);
          
          const existingTask = await getTaskConversation(userEmail, taskTitle);
          
          // Create conversation history for LangGraph from taskAgent1 data
          let conversationHistory = "";
          if (existingTask && existingTask.taskStartConvo.length > 0) {
            conversationHistory = existingTask.taskStartConvo
              .map(turn => `User: ${turn.userMessage}\nAgent: ${turn.agentResponse}`)
              .join('\n\n');
          }
          
          // Create temporary conversation state for LangGraph processing
          const tempConversationState = {
            conversation_history: conversationHistory,
            is_complete: false,
            user_email: userEmail
          };
          
          // Process the user's response through LangGraph
          const result = await processUserResponse(userEmail, userResponse, tempConversationState);
          
          // Save to taskAgent1 collection for cloud function architecture
          await addConversationTurn(
            userEmail, 
            taskTitle, 
            userResponse, 
            result.question || "Conversation completed", 
            result.is_complete
          );
          
          // Update recent user activity
          recentUserActivity.set(userEmail, Date.now());
          
          // Send response email if there's a question
          if (result.question && !result.is_complete) {
            // Check throttle before sending
            const waitTime = enforceStrictThrottle(userEmail);
            if (waitTime > 0) {
              console.log(`⏳ Waiting ${waitTime}ms before sending email to ${userEmail}`);
              await new Promise(resolve => setTimeout(resolve, waitTime));
            }
            
            const questionNumber = (result.conversation_history.match(/Question:/g) || []).length + 1;
            const subject = `Prizm Task Question #${questionNumber}`;
            const body = `Hello!

Helen from Prizm here. I have a question for you about your task:

${result.question}

Please reply to this email with your response.

Best regards,
Helen
Prizm Real Estate Concierge Service`;
            
            // Check if we should send this response based on question number
            const shouldSendBasedOnNumber = await shouldSendResponse(userEmail, taskTitle, questionNumber);
            if (!shouldSendBasedOnNumber) {
              console.log(`🚫 Skipping question #${questionNumber} - already responded to this email`);
              await clearEmailLock(userEmail, taskTitle);
              return;
            }
            
            // Check for duplicate before sending
            const shouldSend = await updateLastMsgSent(userEmail, taskTitle, subject, body);
            
            if (shouldSend) {
              // Clear the lock just before sending email
              await clearEmailLock(userEmail, taskTitle);
              await sendEmailViaGCP(userEmail, subject, body);
              // Update last email sent time
              updateLastEmailSentTime(userEmail);
            } else {
              console.log(`🚫 Skipping duplicate email to ${userEmail}`);
              // Clear the lock even if we're not sending (duplicate detected)
              await clearEmailLock(userEmail, taskTitle);
            }
          } else if (result.is_complete) {
            // Check throttle before sending completion email
            const waitTime = enforceStrictThrottle(userEmail);
            if (waitTime > 0) {
              console.log(`⏳ Waiting ${waitTime}ms before sending completion email to ${userEmail}`);
              await new Promise(resolve => setTimeout(resolve, waitTime));
            }
            
            const subject = "Prizm Task Conversation Complete";
            const body = "Thank you for your time. We've completed our conversation about your task.";
            
            // Check for duplicate before sending
            const shouldSend = await updateLastMsgSent(userEmail, taskTitle, subject, body);
            
            if (shouldSend) {
              // Clear the lock just before sending email
              await clearEmailLock(userEmail, taskTitle);
              await sendEmailViaGCP(userEmail, subject, body);
              // Update last email sent time
              updateLastEmailSentTime(userEmail);
            } else {
              console.log(`🚫 Skipping duplicate completion email to ${userEmail}`);
              // Clear the lock even if we're not sending (duplicate detected)
              await clearEmailLock(userEmail, taskTitle);
            }
          } else {
            // No email to send, but clear the lock anyway
            await clearEmailLock(userEmail, taskTitle);
          }
          
          // Mark this email as processed globally
          processingEmails.add(emailUid);
          console.log('Processed email reply for:', userEmail);
          console.log('Total processed emails:', processingEmails.size);
          
        } finally {
          // Always mark as finished processing, even if there was an error
          markEmailAsFinished(emailUid);
          console.log(`✅ Marked email as finished processing: ${emailUid}`);
        }
      });
    });
  });
  
  fetch.once('error', (err) => {
    console.error('Fetch error:', err);
  });
  
  fetch.once('end', () => {
    console.log(`Done fetching all messages from ${folderName}`);
  });
}

// Function to check for new emails and process them
function checkEmails(processedEmails) {
  const imap = createImapConnection();

  imap.once('ready', () => {
    // Search in INBOX folder since [Gmail].All Mail is not accessible
    imap.openBox('INBOX', false, (err, box) => {
      if (err) {
        console.error('Could not open INBOX folder:', err.message);
        imap.end();
        return;
      }
      
      searchForEmails();
      
      function searchForEmails() {
        // Use today's date in DD-MMM-YYYY format for SINCE
        const today = new Date();
        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const day = today.getDate();
        const month = months[today.getMonth()];
        const year = today.getFullYear();
        const imapDate = `${day}-${month}-${year}`;
        
        // Search criteria - look for UNSEEN emails with our subject
        const searchCriteria = [
          'UNSEEN', 
          ['SUBJECT', 'Re: Prizm Task Question'], 
          ['SINCE', imapDate]
        ];
        
        console.log('Searching in INBOX folder');
        console.log('Search criteria:', searchCriteria);
        
        imap.search(searchCriteria, (err, results) => {
          if (err) {
            console.error('Error searching for emails:', err);
            imap.end();
            return;
          }
          
          if (results.length === 0) {
            console.log('No new Prizm email replies found in INBOX');
            imap.end();
            return;
          }
          
          console.log(`Found ${results.length} new Prizm email replies in INBOX`);
          
          // Process the emails found
          processEmailsInFolder(results, 'INBOX', imap, processedEmails);
        });
      }
    });
  });

  imap.once('error', (err) => {
    console.error('IMAP error:', err);
  });

  imap.once('end', () => {
    console.log('IMAP connection ended');
  });

  imap.connect();
}

// Function to start watching for new emails
async function startWatchingEmails() {
  console.log('Starting to watch for new Prizm email replies...');
  
  // Load previously processed email IDs to prevent duplicates across restarts
  const processedEmails = loadProcessedEmails();
  
  // Check immediately
  checkEmails(processedEmails);
  
  // Then check every 1 minute (more frequent for better responsiveness)
  const interval = setInterval(() => {
    checkEmails(processedEmails);
    // Save processed emails periodically to persist across restarts
    saveProcessedEmails(processedEmails);
  }, 1 * 60 * 1000);
  
  // Return function to stop watching
  return () => {
    clearInterval(interval);
    // Save processed emails on shutdown
    saveProcessedEmails(processedEmails);
    console.log('Stopped watching for new emails');
  };
}

// Function to start a new conversation with a user
async function startNewConversation(userEmail) {
  console.log('Starting new conversation with:', userEmail);
  
  // Initialize conversation state
  const conversationState = {
    conversation_history: "",
    is_complete: false,
    user_email: userEmail
  };
  
  // Get the first question from LangGraph
  const result = await processUserResponse(userEmail, "", conversationState);
  
  // Send the first question
  if (result.question) {
    // Check throttle before sending first email
    const waitTime = enforceStrictThrottle(userEmail);
    if (waitTime > 0) {
      console.log(`⏳ Waiting ${waitTime}ms before sending first email to ${userEmail}`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    await sendEmailViaGCP(
      userEmail,
      "Prizm Task Question #1",
      `Hello!

Helen from Prizm here. I have a question for you about your task:

${result.question}

Please reply to this email with your response.

Best regards,
Helen
Prizm Real Estate Concierge Service`
    );
    
    // Update last email sent time
    updateLastEmailSentTime(userEmail);
  }
  
  return result;
}

// Main function to start the email integration
async function main() {
  console.log('Starting LangGraph Email Integration...');
  
  try {
    // Start watching for emails
    const stopWatching = await startWatchingEmails();
    
    console.log('Email integration is running. Press Ctrl+C to stop.');
    
    // Handle graceful shutdown
    process.on('SIGINT', () => {
      console.log('\nShutting down...');
      stopWatching();
      process.exit(0);
    });
    
  } catch (error) {
    console.error('Error starting email integration:', error);
    process.exit(1);
  }
}

// Export functions for use in other modules
module.exports = {
  sendEmailViaGCP,
  processUserResponse,
  checkEmails,
  startWatchingEmails,
  startNewConversation,
  markEmailContentProcessed,
  isEmailContentProcessed,
  enforceStrictThrottle,
  updateLastEmailSentTime
};

// Run the main function if this file is executed directly
if (require.main === module) {
  main();
}

// In-memory email content duplicate detection
function isEmailContentProcessed(userEmail, emailContent) {
  const userData = processedEmailContent.get(userEmail);
  if (!userData) return false;
  
  const contentHash = require('crypto').createHash('md5').update(emailContent).digest('hex');
  const lastProcessed = userData[contentHash];
  
  if (!lastProcessed) return false;
  
  const timeSinceLastProcessed = Date.now() - lastProcessed;
  const DEDUPLICATION_WINDOW = 60000; // 1 minute window
  
  return timeSinceLastProcessed < DEDUPLICATION_WINDOW;
}

function markEmailContentProcessed(userEmail, emailContent) {
  const contentHash = require('crypto').createHash('md5').update(emailContent).digest('hex');
  const timestamp = Date.now();
  
  if (!processedEmailContent.has(userEmail)) {
    processedEmailContent.set(userEmail, {});
  }
  
  processedEmailContent.get(userEmail)[contentHash] = timestamp;
  console.log(`✅ Marked email content as processed for ${userEmail}`);
}

// Function to enforce strict 3-second minimum between emails
function enforceStrictThrottle(userEmail) {
  const now = Date.now();
  const lastSent = lastEmailSentTime.get(userEmail) || 0;
  const timeSinceLastEmail = now - lastSent;
  
  if (timeSinceLastEmail < EMAIL_THROTTLE_MIN_INTERVAL) {
    const waitTime = EMAIL_THROTTLE_MIN_INTERVAL - timeSinceLastEmail;
    console.log(`⏰ STRICT THROTTLE: Must wait ${waitTime}ms before sending email to ${userEmail}`);
    return waitTime;
  }
  
  return 0; // No wait needed
}

// Function to update last email sent time
function updateLastEmailSentTime(userEmail) {
  lastEmailSentTime.set(userEmail, Date.now());
  console.log(`📧 Updated last email sent time for ${userEmail}`);
}

// Simple in-memory email content tracking (no file operations)
function addEmailContentToBuffer(userEmail, emailContent) {
  markEmailContentProcessed(userEmail, emailContent);
  console.log(`📝 Added email content to buffer for ${userEmail}`);
}

// New functions for taskAgent1 collection
async function loadTaskAgentState(customerEmail) {
  if (db) {
    try {
      const docRef = doc(db, 'taskAgent1', customerEmail);
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        console.log(`✅ Loaded taskAgent1 state from Firestore for ${customerEmail}`);
        return docSnap.data();
      }
      return { customerEmail, tasks: {} };
    } catch (error) {
      console.error('Error loading taskAgent1 state from Firestore:', error.message);
      return { customerEmail, tasks: {} };
    }
  } else {
    return { customerEmail, tasks: {} };
  }
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

async function addConversationTurn(customerEmail, taskTitle, userMessage, agentResponse, isComplete = false) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  
  // Initialize task if it doesn't exist
  if (!taskAgentState.tasks[taskTitle]) {
    taskAgentState.tasks[taskTitle] = {
      taskStartConvo: [],
      emailLock: null, // Initialize emailLock field
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
  
  // Add conversation turn
  const turn = {
    timestamp: new Date().toISOString(),
    userMessage: userMessage,
    agentResponse: agentResponse,
    turnNumber: taskAgentState.tasks[taskTitle].taskStartConvo.length + 1,
    isComplete: isComplete,
    conversationId: `${customerEmail}-${taskTitle}-${Date.now()}`
  };
  
  // Append to the entire conversation
  taskAgentState.tasks[taskTitle].taskStartConvo.push(turn);
  taskAgentState.tasks[taskTitle].lastUpdated = new Date().toISOString();
  
  if (isComplete) {
    taskAgentState.tasks[taskTitle].status = 'completed';
  }
  
  await saveTaskAgentState(customerEmail, taskAgentState);
  return turn;
}

async function shouldSendResponse(customerEmail, taskTitle, questionNumber) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  
  if (!taskAgentState.tasks[taskTitle]) {
    return true; // No task exists, safe to send
  }
  
  // If this is question #1, always send
  if (questionNumber === 1) {
    return true;
  }
  
  // If this is question #2 or higher, check if we already sent a response to this email
  // We can determine this by checking if the conversation has more turns than expected
  const conversationTurns = taskAgentState.tasks[taskTitle].taskStartConvo.length;
  const expectedTurns = questionNumber - 1; // For question #2, we should have 1 turn
  
  if (conversationTurns > expectedTurns) {
    console.log(`🚫 Already responded to this email. Question #${questionNumber} requested but conversation has ${conversationTurns} turns (expected ${expectedTurns})`);
    return false;
  }
  
  return true;
}

async function updateLastMsgSent(customerEmail, taskTitle, subject, body) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  
  if (!taskAgentState.tasks[taskTitle]) {
    console.error(`Task ${taskTitle} not found for ${customerEmail}`);
    return false;
  }
  
  // Create hash of the email content for duplicate detection
  const messageHash = require('crypto').createHash('md5').update(`${subject}${body}`).digest('hex');
  
  // Check if this message was already sent
  if (taskAgentState.tasks[taskTitle].lastMsgSent && 
      taskAgentState.tasks[taskTitle].lastMsgSent.messageHash === messageHash) {
    console.log(`🚫 Duplicate message detected for ${customerEmail} - ${taskTitle}`);
    return false; // Don't send duplicate
  }
  
  // Update lastMsgSent
  taskAgentState.tasks[taskTitle].lastMsgSent = {
    timestamp: new Date().toISOString(),
    subject: subject,
    body: body,
    messageHash: messageHash,
    turnNumber: taskAgentState.tasks[taskTitle].taskStartConvo.length
  };
  
  await saveTaskAgentState(customerEmail, taskAgentState);
  console.log(`✅ Updated lastMsgSent for ${customerEmail} - ${taskTitle}`);
  return true; // Safe to send
}

async function getTaskConversation(customerEmail, taskTitle) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  return taskAgentState.tasks[taskTitle] || null;
}

// New functions for distributed locking to prevent duplicate processing
async function acquireEmailLock(customerEmail, taskTitle) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  
  // Initialize task if it doesn't exist
  if (!taskAgentState.tasks[taskTitle]) {
    taskAgentState.tasks[taskTitle] = {
      taskStartConvo: [],
      emailLock: null, // Initialize emailLock field
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
  
  // Wait random amount of time (0-1 second)
  const waitTime = Math.random() * 1000;
  console.log(`⏳ Waiting ${waitTime.toFixed(0)}ms before attempting lock acquisition`);
  await new Promise(resolve => setTimeout(resolve, waitTime));
  
  // Get last 4 digits of high-resolution timestamp
  const timestamp = Date.now();
  const last4Digits = timestamp.toString().slice(-4);
  console.log(`🔒 Attempting to acquire lock with digits: ${last4Digits} (timestamp: ${timestamp})`);
  
  // Check if lock is already taken
  if (taskAgentState.tasks[taskTitle].emailLock !== null) {
    console.log(`🚫 Lock already taken by another responder: ${taskAgentState.tasks[taskTitle].emailLock}`);
    return null; // Lock acquisition failed
  }
  
  // Try to acquire the lock
  taskAgentState.tasks[taskTitle].emailLock = last4Digits;
  taskAgentState.tasks[taskTitle].lastUpdated = new Date().toISOString();
  await saveTaskAgentState(customerEmail, taskAgentState);
  console.log(`✅ Lock acquired: ${last4Digits}`);
  
  // Verify we still have the lock (race condition check)
  const verifyState = await loadTaskAgentState(customerEmail);
  if (verifyState.tasks[taskTitle].emailLock === last4Digits) {
    console.log(`✅ Lock verification successful: ${last4Digits}`);
    return last4Digits; // Lock acquired successfully
  } else {
    console.log(`❌ Lock verification failed. Expected: ${last4Digits}, Got: ${verifyState.tasks[taskTitle].emailLock}`);
    return null; // Lock was taken by another responder
  }
}

async function clearEmailLock(customerEmail, taskTitle) {
  const taskAgentState = await loadTaskAgentState(customerEmail);
  
  if (taskAgentState.tasks[taskTitle]) {
    taskAgentState.tasks[taskTitle].emailLock = null;
    taskAgentState.tasks[taskTitle].lastUpdated = new Date().toISOString();
    await saveTaskAgentState(customerEmail, taskAgentState);
    console.log(`🔓 Cleared email lock for ${customerEmail} - ${taskTitle}`);
  }
}