from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools import repo_tools, doc_tools


def load_rubric() -> Dict:
    """Load rubric.json."""
    try:
        with open("rubric.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Cannot load rubric.json: {e}")


def RepoInvestigator(state: AgentState) -> Dict[str, List[Evidence]]:
    """Repo detective – returns dict of criterion_id → [Evidence]."""
    evidences: Dict[str, List[Evidence]] = {}
    repo_url = state.get("repo_url", "")

    if not repo_url:
        ev = Evidence(
            goal="Repository access",
            found=False,
            location="",
            rationale="repo_url missing",
            confidence=0.0
        )
        return {"general": [ev]}

    try:
        repo_path, success = repo_tools.safe_clone_repo(repo_url)
    except Exception as exc:
        ev = Evidence(
            goal="Repository cloning",
            found=False,
            location=repo_url,
            rationale=f"Clone failed: {exc}",
            confidence=0.0
        )
        return {"general": [ev]}

    if not success:
        return {"general": [Evidence(
            goal="Repository cloning",
            found=False,
            location=repo_url,
            rationale="Clone reported failure",
            confidence=0.0
        )]}

    # Git history evidence (expand for other repo dimensions later)
    try:
        count, commits = repo_tools.extract_git_history(repo_path)
        summary = f"{count} commits. Example: {commits[0]['message'] if commits else 'none'}"
        ev = Evidence(
            goal="Git Forensic Analysis",
            found=count > 3,
            content=summary,
            location=str(repo_path),
            rationale=f"Parsed {count} commits successfully",
            confidence=0.9 if count > 3 else 0.5
        )
        evidences["git_forensic_analysis"] = [ev]
    except Exception as exc:
        evidences["git_forensic_analysis"] = [Evidence(
            goal="Git history",
            found=False,
            location=str(repo_path),
            rationale=f"History extraction failed: {exc}",
            confidence=0.2
        )]

    # TODO: add AST-based checks for graph_orchestration, state_management_rigor, etc.

    return evidences


def DocAnalyst(state: AgentState) -> Dict[str, List[Evidence]]:
    """PDF detective – analyzes rubric dimensions targeting PDF."""
    evidences: Dict[str, List[Evidence]] = {}
    pdf_path_str = state.get("pdf_path", "")

    if not pdf_path_str or not Path(pdf_path_str).is_file():
        ev = Evidence(
            goal="PDF access",
            found=False,
            location="",
            rationale="pdf_path missing or invalid",
            confidence=0.0
        )
        return {"general": [ev]}

    pdf_path = Path(pdf_path_str)
    pdf_data = doc_tools.extract_pdf_content(pdf_path)

    if not pdf_data["success"]:
        ev = Evidence(
            goal="PDF extraction",
            found=False,
            location=str(pdf_path),
            rationale=" → ".join(pdf_data["errors"]),
            confidence=0.1
        )
        return {"general": [ev]}

    chunks = pdf_data["chunks"]
    image_count = len(pdf_data["image_paths"])

    rubric = load_rubric()
    pdf_dims = [d for d in rubric["dimensions"] if d["target_artifact"] in ("pdf_report", "pdf_images")]

    for dim in pdf_dims:
        dim_id = dim["id"]

        if dim_id == "theoretical_depth":
            keywords = ["Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization"]
            found_kws = []
            for kw in keywords:
                for chunk in chunks:
                    if kw.lower() in chunk["text"].lower():
                        found_kws.append(kw)
                        break
            found = len(found_kws) >= 2
            ev = Evidence(
                goal=dim["name"],
                found=found,
                content=f"Keywords found: {', '.join(found_kws)}",
                location=str(pdf_path),
                rationale=f"{len(found_kws)}/{len(keywords)} architectural terms detected",
                confidence=0.80 if found else 0.40
            )
            evidences[dim_id] = [ev]

        elif dim_id == "report_accuracy":
            # Detect mentioned file paths
            mentioned = re.findall(r'(src/[\w/\-]+\.(py|json|md|toml))', "\n".join(c["text"] for c in chunks))
            unique_files = sorted(set(m[0] for m in mentioned))
            found = len(unique_files) > 0
            ev = Evidence(
                goal=dim["name"],
                found=found,
                content="\n".join(unique_files[:6]) if unique_files else "No paths found",
                location=str(pdf_path),
                rationale=f"{len(unique_files)} potential file references detected",
                confidence=0.70 if found else 0.30
            )
            evidences[dim_id] = [ev]

        elif dim_id == "swarm_visual":
            found = image_count > 0
            ev = Evidence(
                goal=dim["name"],
                found=found,
                content=f"{image_count} images extracted",
                location=str(pdf_path),
                rationale="Images available for future VisionInspector",
                confidence=0.75 if found else 0.25
            )
            evidences[dim_id] = [ev]

    return evidences


def VisionInspector(state: AgentState) -> Dict[str, List[Evidence]]:
    """Placeholder for vision analysis."""
    return {
        "swarm_visual": [Evidence(
            goal="Diagram visual analysis",
            found=False,
            location="",
            rationale="VisionInspector not yet implemented",
            confidence=0.0
        )]
    }