import json
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from src.state import AgentState, JudicialOpinion, Evidence

PROSECUTOR_SYS_PROMPT = """You are the Prosecutor in a Digital Courtroom.
Core Philosophy: "Trust No One. Assume Vibe Coding."
Objective: Scrutinize the evidence for gaps, security flaws, and laziness.

If the rubric asks for "Parallel Orchestration" and the evidence shows "Linear pipeline," argue for a Score of 1. Look specifically for bypassed structure. If Judges return freeform text instead of Pydantic models, charge the defendant with "Hallucination Liability."
Provide a harsh score and a list of specific missing elements.

Evaluate the evidence critically based on the provided dimension and strict rubrics.
"""

DEFENSE_SYS_PROMPT = """You are the Defense Attorney in a Digital Courtroom.
Core Philosophy: "Reward Effort and Intent. Look for the 'Spirit of the Law'."
Objective: Highlight creative workarounds, deep thought, and effort, even if the implementation is imperfect.

If the code is buggy but the architecture report shows deep understanding of LangGraph state reducers, argue that the student matches the "Master Thinker" profile despite syntax errors. Look at the Git History evidence. If the commits tell a story of struggle and iteration, argue for a higher score based on "Engineering Process."
Provide a generous score and highlight strengths.

Evaluate the evidence optimistically based on the provided dimension and rubrics.
"""

TECHLEAD_SYS_PROMPT = """You are the Tech Lead in a Digital Courtroom.
Core Philosophy: "Does it actually work? Is it maintainable?"
Objective: Evaluate architectural soundness, code cleanliness, and practical viability.

Ignore the "Vibe" and the "Struggle." Focus on the Artifacts. Is the operator.add reducer actually used to prevent data overwriting? Are the tool calls isolated and safe? You are the tie-breaker. If the Prosecutor says "1" (Security flaw) and Defense says "5" (Great effort), you assess the Technical Debt.
Provide a realistic score (1, 3, or 5) and technical remediation advice.

Evaluate the evidence practically based on the provided dimension and rubrics.
"""

def _format_evidence(dim_id: str, state: AgentState) -> str:
    # Gather generic evidence and specific evidence
    dim_ev = state["evidences"].get(dim_id, [])
    gen_ev = state["evidences"].get("general", [])
    all_ev = gen_ev + dim_ev
    if not all_ev:
        return "No evidence found."
    lines = []
    for i, ev in enumerate(all_ev):
        lines.append(f"Evidence {i+1}:")
        lines.append(f"  Goal: {ev.goal}")
        lines.append(f"  Found: {ev.found}")
        lines.append(f"  Location: {ev.location}")
        lines.append(f"  Rationale: {ev.rationale}")
        lines.append(f"  Confidence: {ev.confidence}")
        if ev.content:
            lines.append(f"  Content snippet: {ev.content[:500]}...")
    return "\n".join(lines)

def _run_judge(state: AgentState, role_name: str, sys_prompt: str) -> Dict[str, List[JudicialOpinion]]:
    llm = ChatOpenAI(model="gpt-4o", temperature=0.5).with_structured_output(JudicialOpinion)
    
    rubric_dims = state.get("rubric_dimensions", [])
    if not rubric_dims:
        # Load fallback if not in state
        try:
            with open("rubric.json", "r", encoding="utf-8") as f:
                rubric_dims = json.load(f).get("dimensions", [])
        except Exception:
            pass
            
    opinions = []
    for dim in rubric_dims:
        dim_id = dim["id"]
        evidence_text = _format_evidence(dim_id, state)
        
        user_msg = f"""
Criterion: {dim['name']} ({dim_id})
Target Artifact: {dim.get('target_artifact', 'unknown')}
Instruction used by Detectives: {dim.get('forensic_instruction', 'None')}

Success Pattern: {dim.get('success_pattern', 'None')}
Failure Pattern: {dim.get('failure_pattern', 'None')}

Evidence Collected:
{evidence_text}

Submit your JudicialOpinion for this criterion. Ensure your score is between 1 and 5.
Your 'judge' field MUST be '{role_name}'.
Your 'criterion_id' field MUST be '{dim_id}'.
"""
        
        # Retry logic is handled natively by some LangChain versions, but we can do a simple loop if it fails
        max_retries = 2
        for attempt in range(max_retries):
            try:
                op = llm.invoke([
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content=user_msg)
                ])
                # Enforce the correct literal name and criterion id
                op.judge = role_name
                op.criterion_id = dim_id
                opinions.append(op)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    # Fallback on failure
                    opinions.append(JudicialOpinion(
                        judge=role_name, # type: ignore
                        criterion_id=dim_id,
                        score=3,
                        argument=f"Failed to generate structured opinion due to parser error: {e}",
                        cited_evidence=[]
                    ))
                    
    return {"opinions": opinions}

def Prosecutor(state: AgentState) -> Dict[str, List[JudicialOpinion]]:
    return _run_judge(state, "Prosecutor", PROSECUTOR_SYS_PROMPT)

def Defense(state: AgentState) -> Dict[str, List[JudicialOpinion]]:
    return _run_judge(state, "Defense", DEFENSE_SYS_PROMPT)

def TechLead(state: AgentState) -> Dict[str, List[JudicialOpinion]]:
    return _run_judge(state, "TechLead", TECHLEAD_SYS_PROMPT)
