import json
from typing import Dict, List, Any
from pathlib import Path

from src.state import AgentState, JudicialOpinion, CriterionResult, AuditReport

def load_rubric() -> Dict:
    try:
        with open("rubric.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Cannot load rubric.json: {e}")

def _generate_markdown_report(report: AuditReport, output_dir: str = "audit"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    md = []
    md.append(f"# Audit Report for {report.repo_url}\n")
    md.append("## Executive Summary")
    md.append(report.executive_summary)
    md.append(f"\n**Overall Score: {report.overall_score:.2f} / 5.00**\n")
    
    md.append("## Criterion Breakdown")
    for cr in report.criteria:
        md.append(f"### {cr.dimension_name}")
        md.append(f"**Final Score:** {cr.final_score} / 5")
        
        if cr.dissent_summary:
            md.append("\n> **Dissent / Conflict Notice:**")
            md.append(f"> {cr.dissent_summary}\n")
            
        md.append("#### Judge Opinions:")
        for op in cr.judge_opinions:
            md.append(f"- **{op.judge} (Score: {op.score}):** {op.argument}")
            
        md.append(f"\n#### Remediation:")
        md.append(cr.remediation)
        md.append("\n---\n")
        
    md.append("## Complete Remediation Plan")
    md.append(report.remediation_plan)
    
    with open(f"{output_dir}/report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

def ChiefJusticeNode(state: AgentState) -> Dict[str, Any]:
    rubric = load_rubric()
    dimensions = rubric.get("dimensions", [])
    
    opinions = state.get("opinions", [])
    evidences = state.get("evidences", {})
    
    # Group opinions by criterion_id
    opinions_by_crit: Dict[str, List[JudicialOpinion]] = {}
    for op in opinions:
        opinions_by_crit.setdefault(op.criterion_id, []).append(op)
        
    crit_results = []
    total_score = 0
    
    for dim in dimensions:
        dim_id = dim["id"]
        dim_name = dim["name"]
        
        ops = opinions_by_crit.get(dim_id, [])
        prosecutor_op = next((o for o in ops if o.judge == "Prosecutor"), None)
        defense_op = next((o for o in ops if o.judge == "Defense"), None)
        tech_lead_op = next((o for o in ops if o.judge == "TechLead"), None)
        
        p_score = prosecutor_op.score if prosecutor_op else 3
        d_score = defense_op.score if defense_op else 3
        t_score = tech_lead_op.score if tech_lead_op else 3
        
        final_score = round((p_score + d_score + t_score) / 3)
        dissent_summary = None
        
        # Determine evidence presence
        dim_evs = evidences.get(dim_id, [])
        all_found = all(e.found for e in dim_evs) if dim_evs else False
        
        # Rule of Security
        if dim_id == "safe_tool_engineering" and p_score <= 2:
            final_score = min(final_score, 3)
            dissent_summary = "Security Rule Applied: Prosecutor identified flaws; score capped at 3."
            
        # Rule of Evidence (Fact Supremacy)
        if not all_found and d_score >= 4:
             final_score = p_score
             dissent_summary = "Fact Supremacy Rule Applied: Artifact missing but Defense gave high score. Overruled."
             
        # Rule of Functionality
        if dim_id in ["graph_orchestration", "state_management_rigor"] and t_score >= 4:
             final_score = t_score
             dissent_summary = "Functionality Weight Rule Applied: Tech Lead confirmed modular workable architecture, carrying highest weight."

        # Variance Dissent
        variance = max([p_score, d_score, t_score]) - min([p_score, d_score, t_score])
        if variance > 2 and not dissent_summary:
            final_score = t_score  # Fallback to TechLead tied breaker 
            dissent_summary = f"High variance ({variance}) detected between Prosecutor ({p_score}) and Defense ({d_score}). TechLead ({t_score}) acts as tie-breaker."
            
        final_score = max(1, min(final_score, 5))
        total_score += final_score
        
        remediation_text = tech_lead_op.argument if tech_lead_op else "Please review this component thoroughly."
        
        crit_results.append(CriterionResult(
            dimension_id=dim_id,
            dimension_name=dim_name,
            final_score=final_score,
            judge_opinions=ops,
            dissent_summary=dissent_summary,
            remediation=remediation_text
        ))
        
    overall = total_score / len(dimensions) if dimensions else 0.0
    
    report = AuditReport(
        repo_url=state.get("repo_url", "Unknown Repository"),
        executive_summary=f"Automated Audit Complete. Evaluated {len(dimensions)} dimensions. Overall synthesis resulted in a score of {overall:.2f}.",
        overall_score=overall,
        criteria=crit_results,
        remediation_plan="Review the individual criterion remediations above, particularly prioritizing dimensions scoring 3 or below."
    )
    
    _generate_markdown_report(report)
    
    return {"final_report": report}
