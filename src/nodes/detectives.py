from __future__ import annotations

from pathlib import Path
from typing import Dict

from pydantic import BaseModel

from src.state import AgentState, Evidence
from src.tools import repo_tools, doc_tools


def RepoInvestigator(state: AgentState) -> Evidence:
    """Detective node that inspects the git repository.

    This function clones the repo specified in ``state.repo_url`` using
    :func:`repo_tools.safe_clone_repo`, extracts a brief commit history, and
    returns an ``Evidence`` object describing what was found. Any errors are
    caught and reported via ``found=False`` rather than raising.
    """
    goal = "git history overview"
    repo_url = state.get("repo_url", "")
    if not repo_url:
        return Evidence(
            goal=goal,
            found=False,
            location="",
            rationale="repo_url missing from state",
            confidence=0.0,
        )

    try:
        repo_path, success = repo_tools.safe_clone_repo(repo_url)
    except Exception as exc:
        return Evidence(
            goal=goal,
            found=False,
            location=repo_url,
            rationale=f"clone failed: {exc}",
            confidence=0.0,
        )

    if not success:
        return Evidence(
            goal=goal,
            found=False,
            location=repo_url,
            rationale="clone command reported failure",
            confidence=0.0,
        )

    try:
        count, commits = repo_tools.extract_git_history(repo_path)
        summary = f"{count} commits, first: {commits[0]['message'] if commits else 'n/a'}"
        rationale = "Repository successfully cloned and history parsed."
        confidence = 0.8
    except Exception as exc:
        summary = ""
        rationale = f"history extraction failed: {exc}"
        confidence = 0.3

    return Evidence(
        goal=goal,
        found=True,
        content=summary,
        location=str(repo_path),
        rationale=rationale,
        confidence=confidence,
    )


def DocAnalyst(state: AgentState) -> Evidence:
    """Detective node that examines a PDF artifact from state.pdf_path.

    The function loads the file, extracts text and up to 5 images, and
    returns an ``Evidence`` object summarizing the results. If the path is
    missing or unreadable, ``found`` is set to False with an explanatory
    rationale.
    """
    goal = "pdf report inspection"
    pdf_path = state.get("pdf_path", "")
    if not pdf_path:
        return Evidence(
            goal=goal,
            found=False,
            location="",
            rationale="pdf_path missing from state",
            confidence=0.0,
        )
    path_obj = Path(pdf_path)
    try:
        text, images = doc_tools.extract_pdf_text_and_images(path_obj)
        summary = f"extracted {len(text.splitlines())} lines and {len(images)} images"
        rationale = "PDF parsed successfully"
        confidence = 0.7
        return Evidence(
            goal=goal,
            found=True,
            content=summary,
            location=pdf_path,
            rationale=rationale,
            confidence=confidence,
        )
    except Exception as exc:
        return Evidence(
            goal=goal,
            found=False,
            location=pdf_path,
            rationale=f"PDF parsing failed: {exc}",
            confidence=0.0,
        )


def VisionInspector(state: AgentState) -> Evidence:
    """Placeholder for an optional image analysis detective.

    Full implementation is deferred; returns a skipped evidence object.
    """
    return Evidence(
        goal="vision inspection",
        found=False,
        location="",
        rationale="VisionInspector not yet implemented",
        confidence=0.0,
    )
