import os
import uuid
from typing import TypedDict
import streamlit as st
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

st.set_page_config(page_title="Multi-Agent Code Reviewer", page_icon="🤖", layout="wide")

# --- 1. Session & Memory Tracking ---
# This ensures Streamlit remembers the exact paused state of your graph
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "memory" not in st.session_state:
    st.session_state.memory = MemorySaver()

# --- 2. Sidebar Configuration ---
with st.sidebar:
    st.header("🔑 API Configuration")
    user_api_key = st.text_input("Enter your Gemini API Key", type="password")
    st.markdown("[Get your free API key here](https://aistudio.google.com/app/apikey)")
    st.divider()
    
    # Failsafe to clear the graph's memory if you want to start fresh
    if st.button("Reset Session Memory"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.memory = MemorySaver()
        st.success("Memory wiped. Ready for a new review.")
        st.rerun()

# --- 3. Shared Memory State ---
class AgentState(TypedDict):
    pr_diff: str               
    security_feedback: str     
    performance_feedback: str  
    style_feedback: str        
    final_summary: str         

# --- 4. The Orchestration Pipeline ---
def compile_graph(api_key):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key, temperature=0)

    def security_agent(state: AgentState):
        sys_prompt = "You are an expert cybersecurity engineer. Review for SQL injection, XSS, and vulnerabilities. Be concise."
        return {"security_feedback": llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=state["pr_diff"])]).content}

    def performance_agent(state: AgentState):
        sys_prompt = "You are a performance optimization engineer. Review for Big-O complexity and memory leaks. Be concise."
        return {"performance_feedback": llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=state["pr_diff"])]).content}

    def style_agent(state: AgentState):
        sys_prompt = "You are a strict Python PEP8 reviewer. Check formatting and naming. Be concise."
        return {"style_feedback": llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=state["pr_diff"])]).content}

    def aggregator_orchestrator(state: AgentState):
        sys_prompt = "You are a Lead DevOps Engineer. Synthesize the reports into Markdown. Prioritize security."
        combined_input = f"Security: {state.get('security_feedback')}\nPerformance: {state.get('performance_feedback')}\nStyle: {state.get('style_feedback')}"
        return {"final_summary": llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=combined_input)]).content}

    workflow = StateGraph(AgentState)
    workflow.add_node("security", security_agent)
    workflow.add_node("performance", performance_agent)
    workflow.add_node("style", style_agent)
    workflow.add_node("orchestrator", aggregator_orchestrator)

    workflow.add_edge(START, "security")
    workflow.add_edge("security", "performance")
    workflow.add_edge("performance", "style")
    workflow.add_edge("style", "orchestrator")
    workflow.add_edge("orchestrator", END)

    # THE CRITICAL HITL ADDITION: We attach the memory and set the breakpoint
    return workflow.compile(
        checkpointer=st.session_state.memory,
        interrupt_before=["orchestrator"]
    )

# --- 5. Streamlit UI Routing ---
st.title("🤖 AI Multi-Agent Code Reviewer (HITL Edition)")
st.write("Submit code. The graph will pause after the initial agent reviews, requiring your human approval before compiling the final report.")
st.divider()

# --- NEW: Restored File Uploader Input Block ---
st.subheader("1. Input Source Code")
uploaded_file = st.file_uploader("Upload a Python file (.py)", type=["py"])

# Determine code source (upload vs manual paste)
if uploaded_file is not None:
    code_to_review = uploaded_file.getvalue().decode("utf-8")
    st.success(f"Successfully loaded: {uploaded_file.name}")
    with st.expander("Preview Uploaded Code"):
        st.code(code_to_review, language="python")
else:
    code_to_review = st.text_area("Or paste your Python code manually:", height=200)

st.divider()
st.subheader("2. Execute Audit")

# Define the config with our persistent thread_id so the graph knows which memory to load
config = {"configurable": {"thread_id": st.session_state.thread_id}}

# ... [The rest of the if user_api_key: logic stays exactly the same]