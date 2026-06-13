import os
from typing import TypedDict
import streamlit as st
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

st.set_page_config(page_title="Multi-Agent Code Reviewer", page_icon="🤖", layout="wide")

# --- 1. Sidebar Configuration (BYOK Security) ---
with st.sidebar:
    st.header("🔑 API Configuration")
    st.write("This tool uses Google's Gemini 2.5 Flash model.")
    # The password type hides the key as they type it
    user_api_key = st.text_input("Enter your Gemini API Key", type="password")
    st.markdown("[Get your free API key here](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.caption("Security Note: Your key is never stored or logged. It is only used for this temporary session.")

# --- 2. Shared Memory State ---
class AgentState(TypedDict):
    pr_diff: str               
    security_feedback: str     
    performance_feedback: str  
    style_feedback: str        
    final_summary: str         

# --- 3. The Orchestration Pipeline ---
# We wrap this in a function so it can dynamically accept the user's API key
def run_audit_pipeline(code_snippet, api_key):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key, temperature=0)

    def security_agent(state: AgentState):
        sys_prompt = "You are an expert cybersecurity engineer. Review the provided code diff for SQL injection, XSS, hardcoded secrets, and vulnerabilities. Be concise."
        messages = [SystemMessage(content=sys_prompt), HumanMessage(content=state["pr_diff"])]
        return {"security_feedback": llm.invoke(messages).content}

    def performance_agent(state: AgentState):
        sys_prompt = "You are a performance optimization engineer. Review the code diff for Big-O complexity issues, memory leaks, and inefficient loops. Be concise."
        messages = [SystemMessage(content=sys_prompt), HumanMessage(content=state["pr_diff"])]
        return {"performance_feedback": llm.invoke(messages).content}

    def style_agent(state: AgentState):
        sys_prompt = "You are a strict Python PEP8 reviewer. Check for bad variable naming, lack of modularity, and poor formatting. Be concise."
        messages = [SystemMessage(content=sys_prompt), HumanMessage(content=state["pr_diff"])]
        return {"style_feedback": llm.invoke(messages).content}

    def aggregator_orchestrator(state: AgentState):
        sys_prompt = "You are a Lead DevOps Engineer. Synthesize the following three reports into one highly professional Markdown summary. Prioritize security and performance over style."
        combined_input = f"Security: {state.get('security_feedback')}\nPerformance: {state.get('performance_feedback')}\nStyle: {state.get('style_feedback')}"
        messages = [SystemMessage(content=sys_prompt), HumanMessage(content=combined_input)]
        return {"final_summary": llm.invoke(messages).content}

    # Construct the graph
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

    app = workflow.compile()
    return app.invoke({"pr_diff": code_snippet})

# --- 4. Streamlit UI ---
st.title("🤖 AI Multi-Agent Code Reviewer")
st.caption("Powered by LangGraph & Gemini 2.5 Flash")
st.write("Submit your code snippets below to trigger an automated, multi-perspective architectural audit.")
st.divider()

st.subheader("1. Input Source Code")
uploaded_file = st.file_uploader("Upload a Python file (.py)", type=["py"])

default_bad_code = """def get_user_data(username):
    db = connect_to_db()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    data = db.execute(query)
    results = []
    for x in data:
        for y in data:
            if x == y:
                results.append(x)
                
    API_KEY = "12345-secret-key"
    return results"""

if uploaded_file is not None:
    code_to_review = uploaded_file.getvalue().decode("utf-8")
    st.success(f"Successfully loaded: {uploaded_file.name}")
    with st.expander("Preview Uploaded Code"):
        st.code(code_to_review, language="python")
else:
    code_to_review = st.text_area("Or paste your Python code manually:", value=default_bad_code, height=250)

st.divider()
st.subheader("2. Execute Audit")

if st.button("Run Code Audit", type="primary", use_container_width=True):
    # Safety Check: Did they enter an API key?
    if not user_api_key:
        st.error("⚠️ Please enter your Gemini API Key in the sidebar to run the audit.")
    elif not code_to_review.strip():
        st.warning("⚠️ Please paste or upload some code before running the analysis.")
    else:
        with st.status("Orchestrating AI Agents...", expanded=True) as status:
            status.write("🛡️ Security Agent analyzing vulnerabilities...")
            status.write("⚡ Performance Agent checking time complexity...")
            status.write("💅 Style Agent verifying PEP8 compliance...")
            
            # Run the pipeline with the user's provided key
            output = run_audit_pipeline(code_to_review, user_api_key)
            
            status.update(label="Audit Complete!", state="complete", expanded=False)
        
        st.success("Analysis Compiled Successfully!")
        st.markdown(output["final_summary"])
        
        with st.expander("View Raw Agent Logs"):
            tab1, tab2, tab3 = st.tabs(["Security Feedback", "Performance Feedback", "Style Feedback"])
            with tab1:
                st.markdown(output.get("security_feedback", "No data"))
            with tab2:
                st.markdown(output.get("performance_feedback", "No data"))
            with tab3:
                st.markdown(output.get("style_feedback", "No data"))