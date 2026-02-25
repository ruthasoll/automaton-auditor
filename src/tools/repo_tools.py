import subprocess
import tempfile
from pathlib import Path
from typing import Tuple


class RepoCloneError(Exception):
    """Raised when a repository cannot be cloned successfully."""



def safe_clone_repo(url: str) -> Tuple[Path, bool]:
    """Clone a git repository to a temporary directory safely.

    The clone is shallow (depth 10) and uses ``subprocess.run`` for
    execution. The target directory is returned along with a boolean
    indicating success. Caller is responsible for cleaning up the
    temporary directory (it will be removed automatically once
    the returned :class:`pathlib.Path` object is out of scope if it
    refers to a tempdir context manager, but this function returns the
    actual path - use :func:`shutil.rmtree` or context manager when
    needed).

    Parameters
    ----------
    url : str
        The URL of the repository to clone.

    Returns
    -------
    Tuple[Path, bool]
        A tuple containing the path to the cloned repository and a
        boolean success flag. If cloning failed the directory may still
        exist but the boolean will be ``False``.

    Raises
    ------
    RepoCloneError
        If the git command fails in a way we cannot recover from.
    """
    temp_dir = tempfile.TemporaryDirectory()
    repo_path = Path(temp_dir.name)

    cmd = ["git", "clone", "--depth", "10", url, str(repo_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        # cleanup the temporary directory
        temp_dir.cleanup()
        raise RepoCloneError(
            f"Failed to clone repository {url}: {exc.stderr.strip() or exc.stdout.strip()}"
        )
    # success
    return repo_path, True
