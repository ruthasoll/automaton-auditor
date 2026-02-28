import pytest
from unittest.mock import patch, MagicMock
from src.state import AgentState, Evidence
from src.nodes.judges import Prosecutor, Defense, TechLead, JudicialOpinion

@pytest.fixture
def mock_state() -> AgentState:
    return {
        "repo_url": "https://github.com/example/test",
        "pdf_path": "test.pdf",
        "rubric_dimensions": [
            {
                "id": "dimension_test",
                "name": "Test Dimension",
                "target_artifact": "github_repo",
                "forensic_instruction": "Find X",
                "success_pattern": "X is good",
                "failure_pattern": "X is bad"
            }
        ],
        "evidences": {
            "dimension_test": [
                 Evidence(
                    goal="Find X",
                    found=True,
                    content="X=1",
                    location="test.py",
                    rationale="Found X",
                    confidence=1.0
                )
            ]
        },
        "opinions": [],
        "final_report": None
    }

@patch('src.nodes.judges.ChatOpenAI')
def test_prosecutor_node(mock_chat, mock_state):
    # Setup mock LLM structured output
    mock_llm_instance = MagicMock()
    mock_chat.return_value.with_structured_output.return_value = mock_llm_instance
    
    # The model should return a valid JudicialOpinion
    mock_llm_instance.invoke.return_value = JudicialOpinion(
        judge="Prosecutor",
        criterion_id="dimension_test",
        score=2,
        argument="I found flaws as the Prosecutor.",
        cited_evidence=["test.py"]
    )
    
    # Run the node
    result = Prosecutor(mock_state)
    opinions = result["opinions"]
    
    assert len(opinions) == 1
    assert opinions[0].judge == "Prosecutor"
    assert opinions[0].score == 2
    assert opinions[0].criterion_id == "dimension_test"
    
@patch('src.nodes.judges.ChatOpenAI')
def test_defense_node(mock_chat, mock_state):
    # Setup mock LLM structured output
    mock_llm_instance = MagicMock()
    mock_chat.return_value.with_structured_output.return_value = mock_llm_instance
    
    # The model should return a valid JudicialOpinion
    mock_llm_instance.invoke.return_value = JudicialOpinion(
        judge="Defense",
        criterion_id="dimension_test",
        score=4,
        argument="I found great effort here.",
        cited_evidence=["test.py"]
    )
    
    result = Defense(mock_state)
    opinions = result["opinions"]
    
    assert len(opinions) == 1
    assert opinions[0].judge == "Defense"
    assert opinions[0].score == 4

@patch('src.nodes.judges.ChatOpenAI')
def test_techlead_node(mock_chat, mock_state):
    # Setup mock LLM structured output
    mock_llm_instance = MagicMock()
    mock_chat.return_value.with_structured_output.return_value = mock_llm_instance
    
    # The model should return a valid JudicialOpinion
    mock_llm_instance.invoke.return_value = JudicialOpinion(
        judge="TechLead",
        criterion_id="dimension_test",
        score=3,
        argument="It works, but maintainability is average.",
        cited_evidence=["test.py"]
    )
    
    result = TechLead(mock_state)
    opinions = result["opinions"]
    
    assert len(opinions) == 1
    assert opinions[0].judge == "TechLead"
    assert opinions[0].score == 3
