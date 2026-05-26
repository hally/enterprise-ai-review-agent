from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import Any, Dict, List
import json

# Initialize OpenAI model
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

# Define the state structure
class AgentState(BaseModel):
    problem: str
    architecture_review: str = ""
    cost_review: str = ""
    security_review: str = ""
    final_report: str = ""
    messages: List[Dict[str, str]] = []

# Architecture Agent
def architecture_agent(state: AgentState) -> AgentState:
    prompt = f"""You are an Enterprise Architecture Expert. Review this technical problem and provide architectural feedback.

Problem: {state.problem}

Provide a concise architectural review covering:
1. Is the architecture sound?
2. What are the potential bottlenecks?
3. What improvements would you suggest?

Keep your response to 2-3 paragraphs."""
    
    response = llm.invoke(prompt)
    state.architecture_review = response.content
    state.messages.append({"role": "architecture_agent", "content": response.content})
    return state

# Cost Agent
def cost_agent(state: AgentState) -> AgentState:
    prompt = f"""You are a Cloud Cost Optimization Expert. Review this architecture for cost implications.

Problem: {state.problem}

Architecture Review so far: {state.architecture_review}

Provide cost analysis covering:
1. What are the primary cost drivers?
2. Where can costs be optimized?
3. What's the estimated cost range for this solution?

Keep your response to 2-3 paragraphs."""
    
    response = llm.invoke(prompt)
    state.cost_review = response.content
    state.messages.append({"role": "cost_agent", "content": response.content})
    return state

# Security Agent
def security_agent(state: AgentState) -> AgentState:
    prompt = f"""You are a Security & Compliance Expert. Review this architecture for security risks.

Problem: {state.problem}

Architecture Review: {state.architecture_review}
Cost Review: {state.cost_review}

Provide security analysis covering:
1. What are the security risks?
2. What compliance requirements apply?
3. What security improvements would you recommend?

Keep your response to 2-3 paragraphs."""
    
    response = llm.invoke(prompt)
    state.security_review = response.content
    state.messages.append({"role": "security_agent", "content": response.content})
    return state

# Orchestrator: Synthesize all reviews
def synthesize_report(state: AgentState) -> AgentState:
    prompt = f"""You are a Chief Architect. Synthesize the following reviews into a comprehensive final report.

Original Problem: {state.problem}

Architecture Review: {state.architecture_review}

Cost Review: {state.cost_review}

Security Review: {state.security_review}

Create a final executive summary that:
1. Summarizes key findings from all three reviews
2. Identifies the top 3 recommendations
3. Provides an implementation priority

Format as a professional report."""
    
    response = llm.invoke(prompt)
    state.final_report = response.content
    state.messages.append({"role": "orchestrator", "content": response.content})
    return state

# Build the graph
def build_graph():
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("architecture_agent", architecture_agent)
    graph.add_node("cost_agent", cost_agent)
    graph.add_node("security_agent", security_agent)
    graph.add_node("synthesize", synthesize_report)
    
    # Define edges - agents work sequentially, each building on previous
    graph.add_edge("architecture_agent", "cost_agent")
    graph.add_edge("cost_agent", "security_agent")
    graph.add_edge("security_agent", "synthesize")
    graph.add_edge("synthesize", END)
    
    # Set entry point
    graph.set_entry_point("architecture_agent")
    
    return graph.compile()

# Main function to run the agent
def run_agent_review(problem: str) -> Dict[str, Any]:
    """Run the multi-agent review system"""
    chain = build_graph()
    
    initial_state = AgentState(problem=problem)
    result = chain.invoke(initial_state)
    
    return {
        "problem": result.problem,
        "architecture_review": result.architecture_review,
        "cost_review": result.cost_review,
        "security_review": result.security_review,
        "final_report": result.final_report,
        "all_messages": result.messages
    }
