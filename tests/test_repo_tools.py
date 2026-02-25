import os
import tempfile
from pathlib import Path
import subprocess

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
