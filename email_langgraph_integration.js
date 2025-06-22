const nodemailer = require('nodemailer');
const Imap = require('imap');
const { simpleParser } = require('mailparser');
const axios = require('axios');
// const { initializeApp } = require('firebase/app');
// const { getFirestore, doc, getDoc, setDoc, collection } = require('firebase/firestore');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Firebase configuration - DISABLED for now
// const firebaseConfig = {
//   apiKey: process.env.FIREBASE_API_KEY,
//   authDomain: process.env.FIREBASE_AUTH_DOMAIN,
//   projectId: process.env.FIREBASE_PROJECT_ID,
//   storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
//   messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
//   appId: process.env.FIREBASE_APP_ID
// };

// Initialize Firebase - DISABLED for now
let db = null;
// try {
//   const app = initializeApp(firebaseConfig);
//   db = getFirestore(app);
//   console.log('✅ Firebase initialized successfully');
//   console.log('📁 Using Firestore for conversation states');
//   console.log('📧 Using Firestore for duplicate email tracking');
// } catch (error) {
//   console.warn('⚠️ Firebase not configured, falling back to file-based storage');
//   console.warn('Set FIREBASE_* environment variables to use Firestore');
// }

console.log('📁 Using file-based storage for conversation states');
console.log('📧 Using file-based storage for duplicate email tracking');

// Debug: Check if environment variables are loaded
console.log('Gmail User:', process.env.GMAIL_USER);
console.log('App Password length:', process.env.GMAIL_APP_PASSWORD ? process.env.GMAIL_APP_PASSWORD.length : 0);
console.log('Email Function URL:', process.env.EMAIL_FUNCTION_URL);

// File to store conversation states persistently
const CONVERSATION_STATES_FILE = 'conversation_states.json';
// File to store processed email IDs persistently
const PROCESSED_EMAILS_FILE = 'processed_emails.json';

// Track recent user activity to prevent duplicate processing
const recentUserActivity = new Map(); // userEmail -> timestamp
const DEDUPLICATION_WINDOW = 60000; // 60 seconds in milliseconds

// Track emails being processed in current session to prevent race conditions
const processingEmails = new Set(); // email UIDs currently being processed

const watcherStartTime = Date.now(); // Record watcher start time

// Function to check if user has been processed recently
function isUserRecentlyProcessed(userEmail) {
  const now = Date.now();
  const lastProcessed = recentUserActivity.get(userEmail);
  
  if (lastProcessed && (now - lastProcessed) < DEDUPLICATION_WINDOW) {
    console.log(`⏰ Skipping email from ${userEmail} - processed ${Math.round((now - lastProcessed) / 1000)}s ago (within ${DEDUPLICATION_WINDOW / 1000}s window)`);
    return true;
  }
  
  // Update the timestamp
  recentUserActivity.set(userEmail, now);
  return false;
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
      const conversationStates = {};
      // Note: In a real implementation, you'd want to paginate this
      // For now, we'll load states as needed per user
      return conversationStates;
    } catch (error) {
      console.error('Error loading conversation states from Firestore:', error.message);
      return {};
    }
  } else {
    // Fallback to file-based storage
    try {
      if (fs.existsSync(CONVERSATION_STATES_FILE)) {
        const data = fs.readFileSync(CONVERSATION_STATES_FILE, 'utf8');
        return JSON.parse(data);
      }
    } catch (error) {
      console.error('Error loading conversation states from file:', error.message);
    }
    return {};
  }
}

// Function to save conversation state for a specific user
async function saveConversationState(userEmail, conversationState) {
  if (db) {
    try {
      // Save to Firestore
      const userDoc = doc(db, 'conversation_states', userEmail);
      await setDoc(userDoc, {
        ...conversationState,
        lastUpdated: new Date().toISOString()
      });
      console.log(`✅ Saved conversation state to Firestore for ${userEmail}`);
    } catch (error) {
      console.error('Error saving conversation state to Firestore:', error.message);
    }
  } else {
    // Fallback to file-based storage
    try {
      let conversationStates = {};
      if (fs.existsSync(CONVERSATION_STATES_FILE)) {
        const data = fs.readFileSync(CONVERSATION_STATES_FILE, 'utf8');
        conversationStates = JSON.parse(data);
      }
      conversationStates[userEmail] = conversationState;
      fs.writeFileSync(CONVERSATION_STATES_FILE, JSON.stringify(conversationStates, null, 2));
    } catch (error) {
      console.error('Error saving conversation state to file:', error.message);
    }
  }
}

// Function to load conversation state for a specific user
async function loadConversationState(userEmail) {
  if (db) {
    try {
      // Load from Firestore
      const userDoc = doc(db, 'conversation_states', userEmail);
      const docSnap = await getDoc(userDoc);
      if (docSnap.exists()) {
        const data = docSnap.data();
        console.log(`✅ Loaded conversation state from Firestore for ${userEmail}`);
        return data;
      }
    } catch (error) {
      console.error('Error loading conversation state from Firestore:', error.message);
    }
  } else {
    // Fallback to file-based storage
    try {
      if (fs.existsSync(CONVERSATION_STATES_FILE)) {
        const data = fs.readFileSync(CONVERSATION_STATES_FILE, 'utf8');
        const conversationStates = JSON.parse(data);
        return conversationStates[userEmail] || null;
      }
    } catch (error) {
      console.error('Error loading conversation state from file:', error.message);
    }
  }
  return null;
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
    
    if (response.status === 200) {
      console.log('Email sent via GCP function:', subject);
      return true;
    } else {
      console.error('Failed to send email via GCP function:', response.status);
      return false;
    }
  } catch (error) {
    console.error('Error sending email via GCP function:', error.message);
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

// Function to check for new emails and process them
function checkEmails(conversationStates, processedEmails) {
  const imap = createImapConnection();

  imap.once('ready', () => {
    imap.openBox('INBOX', false, (err, box) => {
      if (err) throw err;
      
      // Use today's date in DD-MMM-YYYY format for SINCE
      const today = new Date();
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const day = today.getDate();
      const month = months[today.getMonth()];
      const year = today.getFullYear();
      const imapDate = `${day}-${month}-${year}`;
      console.log('IMAP search date:', imapDate);
      
      // More specific search criteria to avoid duplicates
      // Only look for UNSEEN emails that are replies to our specific questions
      const searchCriteria = [
        'UNSEEN', 
        ['SUBJECT', 'Re: Prizm Task Question'], 
        ['SINCE', imapDate]
      ];
      
      console.log('Search criteria:', searchCriteria);
      
      imap.search(searchCriteria, (err, results) => {
        if (err) throw err;
        
        if (results.length === 0) {
          console.log('No new Prizm email replies');
          imap.end();
          return;
        }

        console.log(`Found ${results.length} new Prizm email replies`);

        // Use markSeen to prevent re-processing and include UIDs
        const fetch = imap.fetch(results, { 
          bodies: '', 
          markSeen: true, 
          struct: true,
          envelope: true,
          uid: true  // This ensures UIDs are included
        });
        
        // Track processed messages in this fetch session
        const processedInSession = new Set();
        
        fetch.on('message', (msg, seqno) => {
          console.log('Processing message #', seqno);
          
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
              console.log('IMAP UID:', uid);
              console.log('Processed emails count:', processedEmails.size);
              console.log('Processed in session:', processedInSession.size);
              console.log('Already processed globally:', processedEmails.has(emailUid));
              console.log('Already processed in session:', processedInSession.has(emailUid));
              console.log('Currently being processed:', isEmailBeingProcessed(emailUid));
              console.log('================================');
              
              // Check if we've already processed this email (global or in this session)
              if (processedEmails.has(emailUid) || processedInSession.has(emailUid)) {
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
                imap.addFlags(msg.attributes.uid, '\\Deleted', (err) => {
                  if (err) {
                    console.error('❌ Failed to mark old email for deletion:', err);
                  } else {
                    console.log('🗑️ Deleted old email (before watcher start):', parsed.subject, parsed.date, parsed.messageId);
                  }
                });
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
                console.log('User response:', userResponse.substring(0, 100) + '...');
                
                // Get or create conversation state for this user
                if (!conversationStates[userEmail]) {
                  // Try to load existing state from storage
                  const existingState = await loadConversationState(userEmail);
                  if (existingState) {
                    conversationStates[userEmail] = existingState;
                    console.log(`✅ Loaded existing conversation state for ${userEmail}`);
                  } else {
                    conversationStates[userEmail] = {
                      conversation_history: "",
                      is_complete: false,
                      user_email: userEmail
                    };
                    console.log(`✅ Created new conversation state for ${userEmail}`);
                  }
                }
                
                // Process the user's response through LangGraph
                const result = await processUserResponse(userEmail, userResponse, conversationStates[userEmail]);
                
                // Update conversation state
                conversationStates[userEmail] = {
                  conversation_history: result.conversation_history,
                  is_complete: result.is_complete,
                  user_email: userEmail
                };
                
                // Save conversation state to storage
                await saveConversationState(userEmail, conversationStates[userEmail]);
                
                // Send the next question if conversation is not complete
                if (!result.is_complete && result.question) {
                  await sendEmailViaGCP(
                    userEmail,
                    `Prizm Task Question #${(result.conversation_history.match(/Question:/g) || []).length + 1}`,
                    `Hello!

Helen from Prizm here. I have a question for you about your task:

${result.question}

Please reply to this email with your response.

Best regards,
Helen
Prizm Real Estate Concierge Service`
                  );
                } else if (result.is_complete) {
                  // Send completion message
                  await sendEmailViaGCP(
                    userEmail,
                    "Prizm Task Conversation Complete",
                    "Thank you for your time. We've completed our conversation about your task."
                  );
                }
                
                // Mark this email as processed globally
                processedEmails.add(emailUid);
                console.log('Processed email reply for:', userEmail);
                console.log('Total processed emails:', processedEmails.size);
                
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
          console.log('Done fetching all messages');
          imap.end();
        });
      });
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
  
  // Store conversation states for each user
  const conversationStates = await loadConversationStates();
  
  // Load previously processed email IDs to prevent duplicates across restarts
  const processedEmails = loadProcessedEmails();
  
  // Check immediately
  checkEmails(conversationStates, processedEmails);
  
  // Then check every 2 minutes (more frequent for better responsiveness)
  const interval = setInterval(() => {
    checkEmails(conversationStates, processedEmails);
    // Save processed emails periodically to persist across restarts
    saveProcessedEmails(processedEmails);
  }, 2 * 60 * 1000);
  
  // Return function to stop watching
  return () => {
    clearInterval(interval);
    // Save processed emails on shutdown
    saveProcessedEmails(processedEmails);
    console.log('Stopped watching for new emails');
    // Note: We don't need to save all states on shutdown since we save per user
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
  startNewConversation
};

// Run the main function if this file is executed directly
if (require.main === module) {
  main();
} 