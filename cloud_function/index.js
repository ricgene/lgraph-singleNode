const functions = require('firebase-functions');
const { getFirestore, doc, getDoc, setDoc } = require('firebase/firestore');
const { initializeApp } = require('firebase/app');
const axios = require('axios');

// Initialize Firebase
const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.FIREBASE_APP_ID
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

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

// Firestore functions
async function loadTaskAgentState(customerEmail) {
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
}

async function saveTaskAgentState(customerEmail, taskAgentState) {
  try {
    const docRef = doc(db, 'taskAgent1', customerEmail);
    await setDoc(docRef, taskAgentState);
    console.log(`✅ Saved taskAgent1 state to Firestore for ${customerEmail}`);
  } catch (error) {
    console.error('Error saving taskAgent1 state to Firestore:', error.message);
  }
}

async function addConversationTurn(customerEmail, taskTitle, userMessage, agentResponse, isComplete = false) {
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
  const crypto = require('crypto');
  const messageHash = crypto.createHash('md5').update(`${subject}${body}`).digest('hex');
  
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

// Email sending function
async function sendEmailViaGCP(to, subject, body) {
  try {
    const response = await axios.post(process.env.EMAIL_FUNCTION_URL, {
      to: to,
      subject: subject,
      body: body
    });
    
    console.log('GCP Email Function Response:');
    console.log('Status:', response.status);
    console.log('Headers:', JSON.stringify(response.headers));
    console.log('Body:', response.data);
    
    if (response.status === 200) {
      console.log(`✅ Email sent successfully to ${to}`);
      return true;
    } else {
      console.error(`❌ Failed to send email to ${to}. Status: ${response.status}`);
      return false;
    }
  } catch (error) {
    console.error(`❌ Error sending email to ${to}:`, error.message);
    return false;
  }
}

// LangGraph processing function
async function processUserResponse(userEmail, userResponse, conversationState) {
  try {
    const response = await axios.post(process.env.LANGGRAPH_SERVER_URL, {
      user_email: userEmail,
      user_response: userResponse,
      conversation_state: conversationState
    });
    
    if (response.status === 200) {
      console.log(`✅ LangGraph processing successful for ${userEmail}`);
      return response.data;
    } else {
      console.error(`❌ LangGraph processing failed for ${userEmail}. Status: ${response.status}`);
      return null;
    }
  } catch (error) {
    console.error(`❌ Error processing with LangGraph for ${userEmail}:`, error.message);
    return null;
  }
}

// Main cloud function
exports.processEmail = functions.https.onRequest(async (req, res) => {
  try {
    console.log('📧 Cloud function triggered');
    console.log('Request method:', req.method);
    console.log('Request headers:', req.headers);
    
    // Handle CORS
    res.set('Access-Control-Allow-Origin', '*');
    res.set('Access-Control-Allow-Methods', 'GET, POST');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
      res.status(204).send('');
      return;
    }
    
    if (req.method !== 'POST') {
      res.status(405).send('Method not allowed');
      return;
    }
    
    const { userEmail, userResponse, taskTitle = "Prizm Task Question" } = req.body;
    
    if (!userEmail || !userResponse) {
      res.status(400).send('Missing required fields: userEmail, userResponse');
      return;
    }
    
    console.log(`📧 Processing email from: ${userEmail}`);
    console.log(`📝 User response: ${userResponse}`);
    console.log(`📋 Task title: ${taskTitle}`);
    
    // Try to acquire email lock to prevent duplicate processing
    const lockAcquired = await acquireEmailLock(userEmail, taskTitle);
    if (!lockAcquired) {
      console.log(`🚫 Failed to acquire lock for ${userEmail} - ${taskTitle}. Another responder is processing this email.`);
      res.status(200).json({ 
        success: false, 
        message: 'Email already being processed by another instance' 
      });
      return;
    }
    
    console.log(`✅ Successfully acquired lock (${lockAcquired}) for ${userEmail} - ${taskTitle}`);
    
    // Get existing task conversation
    const existingTask = await loadTaskAgentState(userEmail);
    const taskData = existingTask.tasks[taskTitle];
    
    // Create conversation history for LangGraph
    let conversationHistory = "";
    if (taskData && taskData.taskStartConvo.length > 0) {
      conversationHistory = taskData.taskStartConvo
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
    
    if (!result) {
      console.log(`❌ LangGraph processing failed for ${userEmail}`);
      await clearEmailLock(userEmail, taskTitle);
      res.status(500).json({ 
        success: false, 
        message: 'Failed to process with LangGraph' 
      });
      return;
    }
    
    // Save to taskAgent1 collection
    await addConversationTurn(
      userEmail, 
      taskTitle, 
      userResponse, 
      result.question || "Conversation completed", 
      result.is_complete
    );
    
    // Send response email if there's a question
    if (result.question && !result.is_complete) {
      const questionNumber = (result.conversation_history.match(/Question:/g) || []).length + 1;
      const subject = `Prizm Task Question`;
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
        res.status(200).json({ 
          success: true, 
          message: 'Email processed but response skipped (duplicate detected)',
          questionNumber: questionNumber
        });
        return;
      }
      
      // Check for duplicate before sending
      const shouldSend = await updateLastMsgSent(userEmail, taskTitle, subject, body);
      
      if (shouldSend) {
        // Clear the lock just before sending email
        await clearEmailLock(userEmail, taskTitle);
        const emailSent = await sendEmailViaGCP(userEmail, subject, body);
        
        if (emailSent) {
          res.status(200).json({ 
            success: true, 
            message: 'Email processed and response sent',
            questionNumber: questionNumber,
            subject: subject
          });
        } else {
          res.status(500).json({ 
            success: false, 
            message: 'Email processed but failed to send response' 
          });
        }
      } else {
        console.log(`🚫 Skipping duplicate email to ${userEmail}`);
        await clearEmailLock(userEmail, taskTitle);
        res.status(200).json({ 
          success: true, 
          message: 'Email processed but response skipped (duplicate detected)',
          questionNumber: questionNumber
        });
      }
    } else if (result.is_complete) {
      const subject = "Prizm Task Conversation Complete";
      const body = "Thank you for your time. We've completed our conversation about your task.";
      
      // Check for duplicate before sending
      const shouldSend = await updateLastMsgSent(userEmail, taskTitle, subject, body);
      
      if (shouldSend) {
        // Clear the lock just before sending email
        await clearEmailLock(userEmail, taskTitle);
        const emailSent = await sendEmailViaGCP(userEmail, subject, body);
        
        if (emailSent) {
          res.status(200).json({ 
            success: true, 
            message: 'Email processed and completion response sent',
            subject: subject
          });
        } else {
          res.status(500).json({ 
            success: false, 
            message: 'Email processed but failed to send completion response' 
          });
        }
      } else {
        console.log(`🚫 Skipping duplicate completion email to ${userEmail}`);
        await clearEmailLock(userEmail, taskTitle);
        res.status(200).json({ 
          success: true, 
          message: 'Email processed but completion response skipped (duplicate detected)' 
        });
      }
    } else {
      // No email to send, but clear the lock anyway
      await clearEmailLock(userEmail, taskTitle);
      res.status(200).json({ 
        success: true, 
        message: 'Email processed but no response needed' 
      });
    }
    
  } catch (error) {
    console.error('❌ Cloud function error:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Internal server error',
      error: error.message 
    });
  }
}); 