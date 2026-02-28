import pytest
from src.state import AgentState, JudicialOpinion, Evidence
from src.nodes.justice import ChiefJusticeNode

def test_chief_justice_node():
    # Setup mock state
    state: AgentState = {
        "repo_url": "https://github.com/example/test",
        "pdf_path": "test.pdf",
        "rubric_dimensions": [
            {
                "id": "safe_tool_engineering",
                "name": "Safe Tool Engineering",
                "target_artifact": "github_repo"
            },
            {
                "id": "graph_orchestration",
                "name": "Graph Orchestration Architecture",
                "target_artifact": "github_repo"
            }
        ],
        "evidences": {
            "safe_tool_engineering": [
                Evidence(
                    goal="Find raw os.system calls",
                    found=True,
                    content="os.system('rm -rf /')",
                    location="src/tools.py",
                    rationale="Raw dangerous call found",
                    confidence=1.0
                )
            ],
            "graph_orchestration": [
                 Evidence(
                    goal="Find graph orchestration",
                    found=False,
                    location="src/graph.py",
                    rationale="Not found",
                    confidence=1.0
                 )
            ]
        },
        "opinions": [
            # Security vulnerability found by Prosecutor
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="safe_tool_engineering",
                score=1,
                argument="Found raw os.system call. Security negligence.",
                cited_evidence=[]
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="safe_tool_engineering",
                score=5, # Defense gives high score ignoring security
                argument="Good effort, tried to clean up files.",
                cited_evidence=[]
            ),
             JudicialOpinion(
                judge="TechLead",
                criterion_id="safe_tool_engineering",
                score=2, 
                argument="Unsafe and unmaintainable.",
                cited_evidence=[]
            ),
            # Missing artifact, Defense hallucinating
             JudicialOpinion(
                judge="Prosecutor",
                criterion_id="graph_orchestration",
                score=1,
                argument="No graph found.",
                cited_evidence=[]
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="graph_orchestration",
                score=5, 
                argument="Deep metacognition shown in the nonexistent graph.",
                cited_evidence=[]
            ),
             JudicialOpinion(
                judge="TechLead",
                criterion_id="graph_orchestration",
                score=1, 
                argument="No implementation.",
                cited_evidence=[]
            )
        ],
        "final_report": None
    }
    
    # Run the node
    result = ChiefJusticeNode(state)
    report = result["final_report"]
    
    # Check that report is generated
    assert report is not None
    assert report.repo_url == "https://github.com/example/test"
    
    # Check criteria results
    safe_tool_result = next(cr for cr in report.criteria if cr.dimension_id == "safe_tool_engineering")
    graph_orch_result = next(cr for cr in report.criteria if cr.dimension_id == "graph_orchestration")
    
    # Rule of Security: overriding score to max 3
    # Prosecutor gave 1, Defense gave 5, TechLead gave 2. Avg is 2.6 -> 3. But cap is 3 anyway.
    assert safe_tool_result.final_score <= 3
    assert "Security Rule Applied" in safe_tool_result.dissent_summary
    
    # Rule of Evidence (Fact Supremacy): Graph orch Defense gave 5, but evidence is missing (found=False)
    # The final score should be overruled to Prosecutor score (1)
    assert graph_orch_result.final_score == 1
    assert "Fact Supremacy Rule Applied" in graph_orch_result.dissent_summary
