import os
import argparse
from dotenv import load_dotenv

load_dotenv()  # loads .env automatically

if not os.getenv("OPENAI_API_KEY"):
    print("Warning: Missing OPENAI_API_KEY in .env")
if not os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGCHAIN_TRACING_V2") == "true":
    print("Warning: LANGCHAIN_API_KEY missing → tracing disabled")

from langgraph.graph import StateGraph, START, END

from src.state import AgentState, AuditReport
from src.nodes.detectives import RepoInvestigator, DocAnalyst, VisionInspector
from src.nodes.judges import Prosecutor, Defense, TechLead
from src.nodes.justice import ChiefJusticeNode

def _cleanup_node(state: AgentState):
    """Cleanup temporary PDF directory if it exists."""
    # Logic to cleanup pdf_temp_dir if it was provided
    temp_dir = state.get("pdf_temp_dir")
    if temp_dir and os.path.exists(temp_dir):
        try:
            from src.tools.doc_tools import cleanup_pdf_temp_dir
            cleanup_pdf_temp_dir(temp_dir)
        except ImportError:
            pass
    return state

def EvidenceAggregator(state: AgentState):
    """Synchronization node (fan-in) before judges."""
    return state

def error_handler(state: AgentState):
    """Output a basic failed report."""
    rep = AuditReport(
        repo_url=state.get("repo_url", "Unknown"),
        executive_summary="Audit failed early due to missing critical evidence (e.g., repo cloning failed or pdf missing).",
        overall_score=0.0,
        criteria=[],
        remediation_plan="Ensure the repository is accessible and the PDF is successfully parsed."
    )
    # Output file
    import os
    os.makedirs("audit", exist_ok=True)
    with open("audit/report.md", "w") as f:
        f.write("# Failed Audit\n\n" + rep.executive_summary)
    return {"final_report": rep}

def check_missing_evidence(state: AgentState):
    """Conditional edge checking if missing key evidences routes to error path."""
    gen_evs = state.get("evidences", {}).get("general", [])
    if any(not ev.found for ev in gen_evs):
        return "error_handler"
    return "judges"

def JudgesBranchNode(state: AgentState):
    """Pass-through node to fan-out to Judges."""
    return state

def build_auditor_graph() -> StateGraph:
    """Create the full StateGraph with parallel detective and judge nodes."""
    builder = StateGraph(AgentState)
    
    # Detectives Layer
    builder.add_node("RepoInvestigator", RepoInvestigator)
    builder.add_node("DocAnalyst", DocAnalyst)
    builder.add_node("VisionInspector", VisionInspector)
    
    # Synchronization
    builder.add_node("EvidenceAggregator", EvidenceAggregator)
    
    # Error Handler
    builder.add_node("error_handler", error_handler)
    
    # Branching node for Judges fan-out
    builder.add_node("JudgesBranchNode", JudgesBranchNode)
    
    # Judicial Layer
    builder.add_node("Prosecutor", Prosecutor)
    builder.add_node("Defense", Defense)
    builder.add_node("TechLead", TechLead)
    
    # Supreme Court
    builder.add_node("ChiefJustice", ChiefJusticeNode)
    
    # Cleanup Node
    builder.add_node("Cleanup", _cleanup_node)
    
    # Detectives Fan-Out
    builder.add_edge(START, "RepoInvestigator")
    builder.add_edge(START, "DocAnalyst")
    builder.add_edge(START, "VisionInspector")
    
    # Detectives Fan-In
    builder.add_edge("RepoInvestigator", "EvidenceAggregator")
    builder.add_edge("DocAnalyst", "EvidenceAggregator")
    builder.add_edge("VisionInspector", "EvidenceAggregator")
    
    # Conditional Edge
    builder.add_conditional_edges(
        "EvidenceAggregator",
        check_missing_evidence,
        {
            "judges": "JudgesBranchNode",
            "error_handler": "error_handler"
        }
    )
    
    # Error path
    builder.add_edge("error_handler", "Cleanup")
    
    # Judges Fan-Out
    builder.add_edge("JudgesBranchNode", "Prosecutor")
    builder.add_edge("JudgesBranchNode", "Defense")
    builder.add_edge("JudgesBranchNode", "TechLead")
    
    # Judges Fan-In
    builder.add_edge("Prosecutor", "ChiefJustice")
    builder.add_edge("Defense", "ChiefJustice")
    builder.add_edge("TechLead", "ChiefJustice")
    
    # Final Output
    builder.add_edge("ChiefJustice", "Cleanup")
    builder.add_edge("Cleanup", END)
    
    return builder

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Automaton Auditor")
    parser.add_argument("--repo", type=str, required=True, help="GitHub repository URL")
    parser.add_argument("--pdf", type=str, required=True, help="Path to the PDF architecture report")
    parser.add_argument("--output", type=str, default="audit/report.md", help="Output path for the Markdown report")
    args = parser.parse_args()
    
    print(f"Starting audit for {args.repo} ...")
    graph = build_auditor_graph().compile()
    
    initial_state = {
        "repo_url": args.repo,
        "pdf_path": args.pdf,
        "rubric_dimensions": [], 
        "evidences": {},
        "opinions": []
    }
    
    # Output file path generation logic is handled inside ChiefJusticeNode using hardcoded 'audit' dir.
    # To use args.output, you could add it to state or just overwrite after.
    # Here we just execute the graph.
    
    try:
        final_state = graph.invoke(initial_state)
        print(f"Audit complete. Report generated at audit/report.md")
    except Exception as e:
        print(f"Audit execution encountered an error: {e}")
