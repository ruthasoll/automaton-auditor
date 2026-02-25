from dotenv import load_dotenv
load_dotenv()  # loads .env automatically
import os

# Optional: quick check (can remove later)
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Missing OPENAI_API_KEY in .env")
if not os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGCHAIN_TRACING_V2") == "true":
    print("Warning: LANGCHAIN_API_KEY missing → tracing disabled")

# partial graph orchestration for Phase 2: detectives only
# try to import real StateGraph from langgraph; provide simple stub if unavailable
try:
    from langgraph import StateGraph
except Exception:  # fallback stub for testing environments
    class StateGraph:
        def __init__(self):
            self.nodes = []
            self.edges = []
        def add_node(self, name, func=None):
            self.nodes.append(name)
        def add_edge(self, src, dst):
            self.edges.append((src, dst))

from src.nodes.detectives import RepoInvestigator, DocAnalyst, VisionInspector


def build_detective_graph() -> StateGraph:
    """Create a minimal StateGraph with parallel detective nodes.

    This graph demonstrates the fan-out/fan-in pattern required by the
    rubric. Judges are intentionally omitted until Phase 3.
    """
    g = StateGraph()
    g.add_node("RepoInvestigator", func=RepoInvestigator)
    g.add_node("DocAnalyst", func=DocAnalyst)
    g.add_node("VisionInspector", func=VisionInspector)
    g.add_node("EvidenceAggregator", func=lambda state: state)

    g.add_edge("START", "RepoInvestigator")
    g.add_edge("START", "DocAnalyst")
    g.add_edge("START", "VisionInspector")

    g.add_edge("RepoInvestigator", "EvidenceAggregator")
    g.add_edge("DocAnalyst", "EvidenceAggregator")
    g.add_edge("VisionInspector", "EvidenceAggregator")

    return g
