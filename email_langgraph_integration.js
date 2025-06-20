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
// } catch (error) {
//   console.warn('⚠️ Firebase not configured, falling back to file-based storage');
//   console.warn('Set FIREBASE_* environment variables to use Firestore');
// }

console.log('📁 Using file-based storage for conversation states');

// Debug: Check if environment variables are loaded
console.log('Gmail User:', process.env.GMAIL_USER);
console.log('App Password length:', process.env.GMAIL_APP_PASSWORD ? process.env.GMAIL_APP_PASSWORD.length : 0);
console.log('Email Function URL:', process.env.EMAIL_FUNCTION_URL);

// File to store conversation states persistently
const CONVERSATION_STATES_FILE = 'conversation_states.json';

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
      
      // Search for unread emails that are replies to our Prizm emails
      // Use a simpler search to avoid unsupported operators
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

        // Use markSeen to prevent re-processing
        const fetch = imap.fetch(results, { bodies: '', markSeen: true });
        
        // Track processed messages in this fetch session
        const processedInSession = new Set();
        
        fetch.on('message', (msg, seqno) => {
          console.log('Processing message #', seqno);
          
          msg.on('body', async (stream) => {
            simpleParser(stream, async (err, parsed) => {
              if (err) throw err;
              
              // Create a unique identifier for this email using multiple fields
              const emailId = `${parsed.messageId || 'no-id'}-${parsed.date || 'no-date'}-${parsed.from.text}-${parsed.subject || 'no-subject'}`;
              
              console.log('Email ID:', emailId);
              console.log('Processed emails count:', processedEmails.size);
              console.log('Processed in session:', processedInSession.size);
              
              // Check if we've already processed this email (global or in this session)
              if (processedEmails.has(emailId) || processedInSession.has(emailId)) {
                console.log('Skipping already processed email:', emailId);
                return;
              }
              
              // Mark as processed in this session immediately
              processedInSession.add(emailId);
              
              // Extract user's email address
              const userEmail = parsed.from.text.match(/<(.+)>/)?.[1] || parsed.from.text;
              
              // Skip processing emails from our own address
              if (userEmail === process.env.GMAIL_USER) {
                console.log('Skipping email from our own address:', userEmail);
                return;
              }
              
              // Extract the user's response from the email body
              const userResponse = parsed.text || parsed.html || '';
              
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
              processedEmails.add(emailId);
              console.log('Processed email reply for:', userEmail);
              console.log('Total processed emails:', processedEmails.size);
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
  
  // Track processed email IDs to prevent duplicates
  const processedEmails = new Set();
  
  // Check immediately
  checkEmails(conversationStates, processedEmails);
  
  // Then check every 2 minutes (more frequent for better responsiveness)
  const interval = setInterval(() => {
    checkEmails(conversationStates, processedEmails);
  }, 2 * 60 * 1000);
  
  // Return function to stop watching
  return () => {
    clearInterval(interval);
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