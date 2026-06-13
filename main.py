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
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key, temperature=0, max_retries=6)

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

    return workflow.compile(
        checkpointer=st.session_state.memory,
        interrupt_before=["orchestrator"]
    )

# --- 5. Streamlit UI Routing ---
st.title("🤖 AI Multi-Agent Code Reviewer (HITL Edition)")
st.write("Submit code. The graph will pause after the initial agent reviews, requiring your human approval before compiling the final report.")
st.divider()

st.subheader("1. Input Source Code")
uploaded_file = st.file_uploader("Upload a Python file (.py)", type=["py"])

if uploaded_file is not None:
    code_to_review = uploaded_file.getvalue().decode("utf-8")
    st.success(f"Successfully loaded: {uploaded_file.name}")
    with st.expander("Preview Uploaded Code"):
        st.code(code_to_review, language="python")
else:
    code_to_review = st.text_area("Or paste your Python code manually:", height=200)

st.divider()
st.subheader("2. Execute Audit")

config = {"configurable": {"thread_id": st.session_state.thread_id}}

if user_api_key:
    app = compile_graph(user_api_key)
    current_state = app.get_state(config)
    
    # --- UI PHASE 2: Graph is Paused at Breakpoint ---
    if "orchestrator" in current_state.next:
        st.warning("✋ **HUMAN IN THE LOOP:** The agents have finished. Review their findings below and approve to compile the final report.")
        
        with st.expander("Review Raw Agent Logs (Click to expand)", expanded=True):
            t1, t2, t3 = st.tabs(["Security", "Performance", "Style"])
            with t1: st.write(current_state.values.get("security_feedback"))
            with t2: st.write(current_state.values.get("performance_feedback"))
            with t3: st.write(current_state.values.get("style_feedback"))
            
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve & Compile Final Report", type="primary", use_container_width=True):
                with st.spinner("Orchestrator compiling..."):
                    app.invoke(None, config) 
                st.rerun()
        with col2:
            if st.button("❌ Reject & Reset", use_container_width=True):
                st.session_state.thread_id = str(uuid.uuid4())
                st.rerun()
                
    # --- UI PHASE 3: Graph is Completed ---
    elif current_state.values.get("final_summary"):
        st.success("Analysis Compiled Successfully!")
        st.markdown(current_state.values.get("final_summary"))
        
        if st.button("Start New Review", use_container_width=True):
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
            
    # --- UI PHASE 1: Graph is Idle (or stuck in an error) ---
    else:
        if st.button("1. Run Initial Agent Review", type="primary", use_container_width=True):
            if not code_to_review.strip():
                st.warning("⚠️ Please paste some code first.")
            else:
                with st.status("Agents analyzing...", expanded=True) as status:
                    app.invoke({"pr_diff": code_to_review}, config)
                    status.update(label="Breakpoint Reached. Awaiting Human Input.", state="complete")
                st.rerun() 
else:
    st.info("👈 Please enter your API key in the sidebar to begin.")