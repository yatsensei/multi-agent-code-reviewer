import os
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

# Load environmental variables from your secret .env file
load_dotenv()

# 1. Define our Shared System Memory State
class AgentState(TypedDict):
    pr_diff: str               # The raw code changes submitted for review
    security_feedback: str     # Notes left by the Security Agent
    performance_feedback: str  # Notes left by the Performance Agent
    style_feedback: str        # Notes left by the Clean Code/Style Agent
    final_summary: str         # The final combined report sent to the user

# 2. Define Empty Dummy Nodes
def security_agent(state: AgentState):
    print("--- Running Security Agent ---")
    return {"security_feedback": "Placeholder: No security flaws detected yet."}

def performance_agent(state: AgentState):
    print("--- Running Performance Agent ---")
    return {"performance_feedback": "Placeholder: Algorithms look efficient."}

def style_agent(state: AgentState):
    print("--- Running Style Agent ---")
    return {"style_feedback": "Placeholder: Code matches style guidelines."}

def aggregator_orchestrator(state: AgentState):
    print("--- Compiling Final Review ---")
    # Combine all findings into a clean layout
    compiled_report = f"### PR Review Report\n\n- **Security:** {state.get('security_feedback')}\n- **Performance:** {state.get('performance_feedback')}\n- **Style:** {state.get('style_feedback')}"
    return {"final_summary": compiled_report}

# 3. Construct the Workflow Flowchart (The Graph)
workflow = StateGraph(AgentState)

# Add our nodes to the graph blueprint
workflow.add_node("security", security_agent)
workflow.add_node("performance", performance_agent)
workflow.add_node("style", style_agent)
workflow.add_node("orchestrator", aggregator_orchestrator)

# Define the execution path using the modern START import
workflow.add_edge(START, "security")
workflow.add_edge("security", "performance")
workflow.add_edge("performance", "style")
workflow.add_edge("style", "orchestrator")
workflow.add_edge("orchestrator", END)

# Compile the graph into an executable application
app = workflow.compile()

# 4. Local Execution Test
if __name__ == "__main__":
    initial_input = {
        "pr_diff": "def add_user(name): execute_sql(f'INSERT INTO users VALUES ({name})')"
    }
    print("Starting Multi-Agent Orchestrator...\n")
    output = app.invoke(initial_input)
    print("\n=== Final System Output ===")
    print(output["final_summary"])