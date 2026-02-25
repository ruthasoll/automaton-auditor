import operator
from typing import Annotated, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

class Evidence(BaseModel):
    """Facts uncovered by a detective agent.

    ``Evidence`` objects are intentionally simple and meant to be appended to
    ``AgentState.evidences`` during the detective phase of the graph. Each
    instance records what we were searching for, whether it was found, where
    it was located, a short rationale, and a confidence score.
    """

    goal: str = Field(..., description="The investigative goal or query string")
    found: bool = Field(..., description="Whether the item was successfully located")
    content: Optional[str] = Field(
        None, description="Optional textual content or summary extracted from the artifact"
    )
    location: str = Field(..., description="Path, URL, or identifier of the artifact")
    rationale: str = Field(..., description="Why the agent believes this evidence is relevant")
    confidence: float = Field(
        ge=0,
        le=1,
        description="Agent's confidence in the accuracy of this evidence (0-1)",
    )

class JudicialOpinion(BaseModel):
    """Opinion produced by a judge on a particular rubric criterion.

    Judges append their opinions to ``AgentState.opinions`` later in the
    graph. Each opinion references a criterion, supplies a 1-5 score,
    justification, and a list of evidence IDs they relied upon.
    """

    judge: Literal["Prosecutor", "Defense", "TechLead"] = Field(
        ..., description="Identity of the judge providing this opinion"
    )
    criterion_id: str = Field(..., description="Identifier of the rubric criterion")
    score: int = Field(ge=1, le=5, description="Numeric score for the criterion")
    argument: str = Field(..., description="Textual reasoning behind the score")
    cited_evidence: List[str] = Field(
        default_factory=list,
        description="List of evidence IDs referenced in this opinion",
    )

class CriterionResult(BaseModel):
    """Aggregated result for a single rubric criterion, including judges' input.

    After the Chief Justice synthesizes opinions, a ``CriterionResult`` is
    created for inclusion in the final audit report.
    """

    dimension_id: str = Field(..., description="Unique ID for this rubric dimension")
    dimension_name: str = Field(..., description="Human-readable name of the dimension")
    final_score: int = Field(
        ge=1, le=5, description="Consensus score after synthesis (1-5)"
    )
    judge_opinions: List[JudicialOpinion] = Field(
        default_factory=list,
        description="All opinions provided by judges for this dimension",
    )
    dissent_summary: Optional[str] = Field(
        None,
        description="Optional summary of any dissenting opinions if they existed",
    )
    remediation: str = Field(..., description="Text describing how to improve or fix issues")

class AuditReport(BaseModel):
    """Final structured report produced by the Chief Justice layer.

    Contains an executive summary, overall score and a list of criterion
    breakdowns along with a remediation plan for the repository under audit.
    """

    repo_url: str = Field(..., description="URL of the audited repository")
    executive_summary: str = Field(..., description="High-level summary of findings")
    overall_score: float = Field(..., description="Weighted overall score across dimensions")
    criteria: List[CriterionResult] = Field(
        default_factory=list,
        description="Detailed results for each rubric criterion",
    )
    remediation_plan: str = Field(..., description="Advice for correcting deficiencies")

class AgentState(TypedDict):
    repo_url: str
    pdf_path: str
    rubric_dimensions: List[Dict]  # loaded from rubric.json
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior]  # merge dicts
    opinions: Annotated[List[JudicialOpinion], operator.add]      # append lists
    final_report: Optional[AuditReport]