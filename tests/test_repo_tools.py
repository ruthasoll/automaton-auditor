import os
import tempfile
from pathlib import Path
import subprocess
import sys

# allow running the test directly by adding workspace src to path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "src"))

import pytest

from src.tools.repo_tools import safe_clone_repo, RepoCloneError


def test_safe_clone_repo_success(tmp_path, monkeypatch):
    # simulate git clone by creating a fake directory instead of actually
    # cloning (network access not guaranteed in tests). we'll monkeypatch
    # subprocess.run to behave like success.
    class DummyResult:
        returncode = 0
        stdout = "Cloned"
        stderr = ""

    def fake_run(cmd, capture_output, text, check):
        assert "git" in cmd[0]
        assert "clone" in cmd
        return DummyResult()

    monkeypatch.setattr("subprocess.run", fake_run)
    path, success = safe_clone_repo("https://example.com/repo.git")
    assert success
    assert isinstance(path, Path)
    # clean up
    if path.exists():
        # temporary directory should still exist; remove it manually
        import shutil

        shutil.rmtree(path)


def test_safe_clone_repo_failure(monkeypatch):
    def fake_run(cmd, capture_output, text, check):
        raise subprocess.CalledProcessError(1, cmd, stderr="error occurred")

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(RepoCloneError):
        safe_clone_repo("https://invalid/url")


def test_extract_git_history(tmp_path):
    # create a temporary git repository with a couple commits
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    # make two commits
    for i in range(2):
        f = repo_dir / f"file{i}.txt"
        f.write_text("hello")
        subprocess.run(["git", "add", str(f)], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", f"commit {i}"], cwd=repo_dir, check=True)
    from src.tools.repo_tools import extract_git_history

    count, commits = extract_git_history(repo_dir)
    assert count == 2
    assert commits[0]["message"].startswith("commit 0")


def test_analyze_graph_structure_simple():
    code = '''
from some import StateGraph

g = StateGraph()
g.add_node("START")
g.add_node("A")
g.add_node("Aggregator")
g.add_edge("START", "A")
g.add_edge("START", "B")
g.add_conditional_edges("A", ["C", "D"])
'''
    from src.tools.repo_tools import analyze_graph_structure

    info = analyze_graph_structure(code)
    assert info["found_stategraph"]
    assert "START" in info["nodes"]
    assert info["fan_out_from_start"]
    assert info["has_aggregator"]
    assert info["has_conditional"]


def test_repoinvestigator_node(tmp_path, monkeypatch):
    """Ensure RepoInvestigator returns appropriate Evidence objects."""
    from src.nodes import RepoInvestigator

    # missing repo_url
    state = {"repo_url": ""}
    ev = RepoInvestigator(state)
    assert not ev.found

    # simulate successful clone and history
    def fake_clone(url):
        return tmp_path, True

    monkeypatch.setattr("src.tools.repo_tools.safe_clone_repo", fake_clone)

    def fake_history(path):
        return 1, [{"hash": "abc", "message": "init"}]

    monkeypatch.setattr("src.tools.repo_tools.extract_git_history", fake_history)
    state = {"repo_url": "https://example.com/repo.git"}
    ev = RepoInvestigator(state)
    assert ev.found
    assert "1 commits" in (ev.content or "")


def test_docanalyst_node(tmp_path):
    from src.nodes import DocAnalyst

    # missing pdf_path
    state = {"pdf_path": ""}
    ev = DocAnalyst(state)
    assert not ev.found

    # create a minimal (invalid) pdf for parsing
    pdf = tmp_path / "empty.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    state = {"pdf_path": str(pdf)}
    ev = DocAnalyst(state)
    assert isinstance(ev.found, bool)
