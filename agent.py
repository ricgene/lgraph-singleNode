from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import Dict, List, Literal, TypedDict, Optional, Any
import json

# Define possible outcomes
OutcomeType = Literal["outcome_a", "outcome_b", "outcome_c", "outcome_d", "needs_more_info"]

# Define our state
class AgentState(TypedDict):
    messages: List  # Main conversation history
    internal_memory: Dict[str, Any]  # Memory for storing intermediate data
    current_question: int  # Which main question we're on
    sub_question_context: Optional[str]  # Context for sub-questions
    sub_question_count: int  # How many sub-questions we've asked in current context
    answers: Dict  # Collected answers
    outcome: OutcomeType  # Determined outcome
    questioning_complete: bool  # Whether we've finished the questioning

# Initialize LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Define the progressive questioning node with memory and sub-questions
async def advanced_questioning(state, user_input=None, stream_handler=None):
    """Conducts a progressive series of questions with memory and sub-questions"""
    messages = state.get("messages", [])
    internal_memory = state.get("internal_memory", {})
    current_question = state.get("current_question", 0)
    sub_question_context = state.get("sub_question_context", None)
    sub_question_count = state.get("sub_question_count", 0)
    answers = state.get("answers", {})
    
    # Main questions to ask in sequence
    main_questions = [
        "What is your primary goal with this product?",
        "How soon do you need this implemented?",
        "What is your budget range for this project?",
        "Have you tried similar solutions before?"
    ]
    
    # If this is the first run, initialize
    if current_question == 0 and not user_input:
        messages.append(AIMessage(content=main_questions[0]))
        return {
            "messages": messages,
            "internal_memory": internal_memory,
            "current_question": current_question,
            "sub_question_context": sub_question_context,
            "sub_question_count": sub_question_count,
            "answers": answers,
            "questioning_complete": False,
            "outcome": "needs_more_info"
        }
    
    # Process user input
    if user_input:
        # Add user response to history
        messages.append(HumanMessage(content=user_input))
        
        # Check if we're in a sub-question context
        if sub_question_context:
            # Process sub-question response
            sub_answer_key = f"{sub_question_context}_sub_{sub_question_count}"
            internal_memory[sub_answer_key] = user_input
            
            # Determine if we need more sub-questions
            need_more_info_prompt = f"""
            Context: {sub_question_context}
            Question: {main_questions[current_question]}
            Previous sub-questions and answers: {json.dumps(internal_memory, indent=2)}
            Latest answer: {user_input}
            
            Based on this information, do we need to ask another follow-up question to fully understand the user's needs?
            If YES, provide the exact follow-up question to ask.
            If NO, write "COMPLETE" and explain why we have sufficient information.
            """
            
            # Get response about whether to continue sub-questions
            if stream_handler:
                follow_up_text = ""
                async for chunk in llm.astream([HumanMessage(content=need_more_info_prompt)]):
                    follow_up_text += chunk.content
                    # Don't stream this decision-making part
            else:
                follow_up = llm.invoke([HumanMessage(content=need_more_info_prompt)])
                follow_up_text = follow_up.content
            
            # Check if we're done with sub-questions
            if "COMPLETE" in follow_up_text:
                # Add a summary of the sub-questions to the main answer
                sub_info_summary_prompt = f"""
                Create a concise summary (1-2 sentences) of what we learned from these sub-questions:
                Context: {sub_question_context}
                Information collected: {json.dumps(internal_memory, indent=2)}
                """
                
                sub_summary = llm.invoke([HumanMessage(content=sub_info_summary_prompt)])
                
                # Store the main answer with sub-info included
                answers[f"question_{current_question}"] = {
                    "main_answer": internal_memory.get(f"{sub_question_context}_sub_0", ""),
                    "sub_info": sub_summary.content,
                    "details": internal_memory
                }
                
                # Move to next main question
                current_question += 1
                sub_question_context = None
                sub_question_count = 0
                
                # Check if we've asked all main questions
                if current_question < len(main_questions):
                    # Ask the next main question
                    if stream_handler:
                        next_q = ""
                        async for chunk in llm.astream([SystemMessage(content=f"Ask this question politely: {main_questions[current_question]}")]):
                            next_q += chunk.content
                            await stream_handler(chunk.content)
                    else:
                        response = llm.invoke([SystemMessage(content=f"Ask this question politely: {main_questions[current_question]}")])
                        next_q = response.content
                    
                    messages.append(AIMessage(content=next_q))
                else:
                    # All main questions answered, determine outcome (code follows later)
                    return await determine_outcome(state, messages, answers, internal_memory, stream_handler)
            else:
                # Extract the follow-up question from the response
                # In practice, you'd want a more robust extraction method
                follow_up_question = follow_up_text.split("\n")[0].replace("YES, ", "")
                
                # Increment sub-question count
                sub_question_count += 1
                
                # Ask the sub-question
                if stream_handler:
                    await stream_handler(follow_up_question)
                messages.append(AIMessage(content=follow_up_question))
        else:
            # Process main question response
            
            # Analyze if we need sub-questions
            sub_question_analysis_prompt = f"""
            Question: {main_questions[current_question]}
            User's answer: {user_input}
            
            Do we need to ask follow-up questions to get more specific information?
            If YES, explain what specific information we need and provide the first follow-up question.
            If NO, just write "SUFFICIENT".
            """
            
            # Get sub-question analysis
            if stream_handler:
                analysis_text = ""
                async for chunk in llm.astream([HumanMessage(content=sub_question_analysis_prompt)]):
                    analysis_text += chunk.content
                    # Don't stream this analysis
            else:
                analysis = llm.invoke([HumanMessage(content=sub_question_analysis_prompt)])
                analysis_text = analysis.content
            
            # Check if we need sub-questions
            if "SUFFICIENT" in analysis_text:
                # Store the main answer directly
                answers[f"question_{current_question}"] = user_input
                
                # Move to next main question
                current_question += 1
                
                # Check if we've asked all main questions
                if current_question < len(main_questions):
                    # Ask the next main question
                    if stream_handler:
                        next_q = ""
                        async for chunk in llm.astream([SystemMessage(content=f"Ask this question politely: {main_questions[current_question]}")]):
                            next_q += chunk.content
                            await stream_handler(chunk.content)
                    else:
                        response = llm.invoke([SystemMessage(content=f"Ask this question politely: {main_questions[current_question]}")])
                        next_q = response.content
                    
                    messages.append(AIMessage(content=next_q))
                else:
                    # All main questions answered, determine outcome
                    return await determine_outcome(state, messages, answers, internal_memory, stream_handler)
            else:
                # Initialize sub-question context
                sub_question_context = f"q{current_question}"
                sub_question_count = 0
                
                # Store the initial answer
                internal_memory[f"{sub_question_context}_sub_0"] = user_input
                internal_memory[f"{sub_question_context}_main_question"] = main_questions[current_question]
                
                # Extract the first sub-question
                # In practice, you'd want a more robust extraction method
                sub_question = analysis_text.split("\n")[-1].replace("First follow-up question: ", "")
                
                # Ask the sub-question
                if stream_handler:
                    await stream_handler(sub_question)
                messages.append(AIMessage(content=sub_question))
        
        return {
            "messages": messages,
            "internal_memory": internal_memory,
            "current_question": current_question,
            "sub_question_context": sub_question_context,
            "sub_question_count": sub_question_count,
            "answers": answers,
            "questioning_complete": False,
            "outcome": "needs_more_info"
        }
    
    # Fallback return if no user input
    return state

# Helper function to determine final outcome
async def determine_outcome(state, messages, answers, internal_memory, stream_handler=None):
    """Determines the final outcome based on all collected information"""
    
    # Combine all information for analysis
    full_context = {
        "answers": answers,
        "internal_memory": internal_memory
    }
    
    # Prompt to determine outcome
    determination_prompt = f"""
    Based on all collected information:
    {json.dumps(full_context, indent=2)}
    
    Analyze the user's needs and determine the most appropriate outcome:
    
    Select one outcome from these options:
    - outcome_a: Small project with tight timeline
    - outcome_b: Complex project with flexible timeline
    - outcome_c: High-budget enterprise implementation
    - outcome_d: Low-cost solution with previous experience
    
    Respond with ONLY one of these outcome letters: outcome_a, outcome_b, outcome_c, or outcome_d
    """
    
    # Get outcome determination
    outcome_response = llm.invoke([HumanMessage(content=determination_prompt)])
    outcome = outcome_response.content.strip().lower()
    
    # Ensure valid outcome
    valid_outcomes = ["outcome_a", "outcome_b", "outcome_c", "outcome_d"]
    if outcome not in valid_outcomes:
        outcome = "outcome_a"  # Default if invalid
    
    # Generate completion message
    completion_prompt = f"""
    Based on our conversation and all the information you've shared:
    {json.dumps(full_context, indent=2)}
    
    I've determined the most appropriate path for you is: {outcome}
    
    Generate a friendly, detailed message explaining this outcome to the user. 
    Reference specific things they mentioned during our conversation, including details from the sub-questions.
    """
    
    if stream_handler:
        completion_text = ""
        async for chunk in llm.astream([HumanMessage(content=completion_prompt)]):
            completion_text += chunk.content
            await stream_handler(chunk.content)
    else:
        completion = llm.invoke([HumanMessage(content=completion_prompt)])
        completion_text = completion.content
    
    messages.append(AIMessage(content=completion_text))
    
    return {
        "messages": messages,
        "internal_memory": internal_memory,
        "current_question": state["current_question"],
        "sub_question_context": None,
        "sub_question_count": 0,
        "answers": answers,
        "questioning_complete": True,
        "outcome": outcome
    }

# Define handlers for each outcome (as in previous example)
def handle_outcome_a(state):
    messages = state["messages"]
    messages.append(AIMessage(content="Processing for Outcome A: Small project with tight timeline"))
    return {"messages": messages}

def handle_outcome_b(state):
    messages = state["messages"]
    messages.append(AIMessage(content="Processing for Outcome B: Complex project with flexible timeline"))
    return {"messages": messages}

def handle_outcome_c(state):
    messages = state["messages"]
    messages.append(AIMessage(content="Processing for Outcome C: High-budget enterprise implementation"))
    return {"messages": messages}

def handle_outcome_d(state):
    messages = state["messages"]
    messages.append(AIMessage(content="Processing for Outcome D: Low-cost solution with previous experience"))
    return {"messages": messages}

# Router function based on questioning completion and outcome
def router(state):
    if not state["questioning_complete"]:
        return "advanced_questioning"
    
    # Route based on determined outcome
    return state["outcome"]

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("advanced_questioning", advanced_questioning)
workflow.add_node("outcome_a", handle_outcome_a)
workflow.add_node("outcome_b", handle_outcome_b)
workflow.add_node("outcome_c", handle_outcome_c)
workflow.add_node("outcome_d", handle_outcome_d)

# Add edges
workflow.add_edge("advanced_questioning", router)
workflow.add_edge("outcome_a", END)
workflow.add_edge("outcome_b", END)
workflow.add_edge("outcome_c", END)
workflow.add_edge("outcome_d", END)

# Set the entry point
workflow.set_entry_point("advanced_questioning")

# Compile the graph
graph = workflow.compile()