const nodemailer = require('nodemailer');
const Imap = require('imap');
const { simpleParser } = require('mailparser');
const axios = require('axios');
require('dotenv').config();

// Import the LangGraph process_message function (we'll need to adapt this)
// For now, we'll simulate the conversation state

// Debug: Check if environment variables are loaded
console.log('Gmail User:', process.env.GMAIL_USER);
console.log('App Password length:', process.env.GMAIL_APP_PASSWORD ? process.env.GMAIL_APP_PASSWORD.length : 0);
console.log('Email Function URL:', process.env.EMAIL_FUNCTION_URL);

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
function checkEmails(conversationStates) {
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
      imap.search(['UNSEEN', ['SUBJECT', 'Re: Prizm Task Question'], ['SINCE', imapDate]], (err, results) => {
        if (err) throw err;
        
        if (results.length === 0) {
          console.log('No new Prizm email replies');
          imap.end();
          return;
        }

        const fetch = imap.fetch(results, { bodies: '' });
        
        fetch.on('message', (msg) => {
          msg.on('body', async (stream) => {
            simpleParser(stream, async (err, parsed) => {
              if (err) throw err;
              
              // Extract user's email address
              const userEmail = parsed.from.text.match(/<(.+)>/)?.[1] || parsed.from.text;
              
              // Extract the user's response from the email body
              const userResponse = parsed.text || parsed.html || '';
              
              console.log('Processing reply from:', userEmail);
              console.log('User response:', userResponse.substring(0, 100) + '...');
              
              // Get or create conversation state for this user
              if (!conversationStates[userEmail]) {
                conversationStates[userEmail] = {
                  conversation_history: "",
                  is_complete: false,
                  user_email: userEmail
                };
              }
              
              // Process the user's response through LangGraph
              const result = await processUserResponse(userEmail, userResponse, conversationStates[userEmail]);
              
              // Update conversation state
              conversationStates[userEmail] = {
                conversation_history: result.conversation_history,
                is_complete: result.is_complete,
                user_email: userEmail
              };
              
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
              
              console.log('Processed email reply for:', userEmail);
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
function startWatchingEmails() {
  console.log('Starting to watch for new Prizm email replies...');
  
  // Store conversation states for each user
  const conversationStates = {};
  
  // Check immediately
  checkEmails(conversationStates);
  
  // Then check every 2 minutes (more frequent for better responsiveness)
  const interval = setInterval(() => {
    checkEmails(conversationStates);
  }, 2 * 60 * 1000);
  
  // Return function to stop watching
  return () => {
    clearInterval(interval);
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

// Example usage
async function main() {
  try {
    console.log('Starting LangGraph Email Integration...');
    
    // Start watching for email replies
    const stopWatching = startWatchingEmails();
    
    // Keep the process running
    process.on('SIGINT', () => {
      console.log('Shutting down...');
      stopWatching();
      process.exit(0);
    });
    
    console.log('Email integration is running. Press Ctrl+C to stop.');
    
  } catch (error) {
    console.error('Error in main:', error);
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