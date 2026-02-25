import ast
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


def extract_git_history(path: Path) -> Tuple[int, list]:
    """Extract a summarized git history from a repository path.

    The function runs ``git log`` with ``--oneline`` and ``--reverse``
    to provide commits from oldest to newest. A simple dict with
    ``hash`` and ``message`` keys is returned for each commit along with
    the total count.

    Parameters
    ----------
    path : Path
        Path to the local git repository.

    Returns
    -------
    Tuple[int, list]
        A tuple containing the number of commits and a list of commit
        dictionaries.

    Raises
    ------
    CalledProcessError
        If the git command fails.
    """
    cmd = [
        "git",
        "-C",
        str(path),
        "log",
        "--oneline",
        "--reverse",
        "--pretty=format:%H %s",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    commits = []
    for line in lines:
        parts = line.split(" ", 1)
        if len(parts) == 2:
            h, msg = parts
            commits.append({"hash": h, "message": msg})
    return len(commits), commits


class GraphASTAnalyzer(ast.NodeVisitor):
    """Visitor that inspects Python source and collects information about a
    ``StateGraph`` usage.

    The analyzer does **not** execute the code; it merely records occurrences
    of graph-related calls and nodes, enabling later assertions about
    structure.
    """

    def __init__(self) -> None:
        self.found_stategraph = False
        self.nodes: list[str] = []
        self.edges: list[tuple[str, str]] = []
        self.conditional_edges: list[tuple[str, str]] = []

    def visit_Call(self, node: ast.Call) -> None:  # type: ignore[override]
        # detect StateGraph instantiation
        if isinstance(node.func, ast.Name) and node.func.id == "StateGraph":
            self.found_stategraph = True

        # detect method calls such as graph.add_node, graph.add_edge
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
            if name == "add_node" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self.nodes.append(arg.value)
            elif name == "add_edge" and len(node.args) >= 2:
                src, dst = node.args[0], node.args[1]
                if (
                    isinstance(src, ast.Constant)
                    and isinstance(src.value, str)
                    and isinstance(dst, ast.Constant)
                    and isinstance(dst.value, str)
                ):
                    self.edges.append((src.value, dst.value))
            elif name == "add_conditional_edges" and len(node.args) >= 2:
                src, dst_list = node.args[0], node.args[1]
                if (
                    isinstance(src, ast.Constant)
                    and isinstance(src.value, str)
                    and isinstance(dst_list, (ast.List, ast.Tuple))
                ):
                    for elt in dst_list.elts:
                        if isinstance(elt, ast.Constant) and isinstance(
                            elt.value, str
                        ):
                            self.conditional_edges.append((src.value, elt.value))
        self.generic_visit(node)


def analyze_graph_structure(code_str: str) -> dict:
    """Parse Python source and return a summary of the graph structure.

    The returned dictionary contains keys:

    - ``found_stategraph`` (bool)
    - ``nodes`` (list[str])
    - ``edges`` (list[tuple[str,str]])
    - ``conditional_edges`` (list[tuple[str,str]])
    - ``fan_out_from_start`` (bool)
    - ``has_aggregator`` (bool)
    - ``has_conditional`` (bool)

    Parameters
    ----------
    code_str : str
        Python source code to analyze.
    """
    tree = ast.parse(code_str)
    analyzer = GraphASTAnalyzer()
    analyzer.visit(tree)
    # compute extras
    fan_out = sum(1 for (s, _) in analyzer.edges if s == "START") > 1
    has_agg = any("aggregator" in n.lower() for n in analyzer.nodes)
    has_cond = len(analyzer.conditional_edges) > 0
    return {
        "found_stategraph": analyzer.found_stategraph,
        "nodes": analyzer.nodes,
        "edges": analyzer.edges,
        "conditional_edges": analyzer.conditional_edges,
        "fan_out_from_start": fan_out,
        "has_aggregator": has_agg,
        "has_conditional": has_cond,
    }
