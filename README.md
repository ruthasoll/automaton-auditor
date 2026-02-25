# automaton-auditor
[![CI](https://github.com/ruthasoll/automaton-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/ruthasoll/automaton-auditor/actions/workflows/ci.yml)

A Week 2 Automaton Auditor skeleton. Current branch implements Phase 1 & 2:
- typed state models
- safe forensic tools
- detective nodes and partial graph orchestration

## Setup

1. Clone the repository and create a Python 3.12 environment (``uv`` is used
   throughout but any venv/conda works):

   ```bash
   git clone <repo-url>
   cd automaton-auditor
   uv env use python@3.12
   uv install
   ```

2. Copy ``.env.example`` to ``.env`` and populate API keys:

   ```bash
   cp .env.example .env
   # edit .env
   ```

3. Install dependencies (dev group included above):

   ```bash
   uv install --dev
   ```

4. Run tests to validate environment:

   ```bash
   python -m pytest -q
   ```

## Running the Detective Graph

Phase 2 exposes a simple graph builder in ``src/graph.py``.  You can load and
execute it like this:

```python
from src.graph import build_detective_graph
from src.state import AgentState

g = build_detective_graph()
state: AgentState = {
    "repo_url": "https://github.com/example/repo.git",
    "pdf_path": "reports/interim_report.pdf",
    "rubric_dimensions": [],
    "evidences": {},
    "opinions": [],
    "final_report": None,
}
print(g.run(state))
```

This graph fans out to three detective nodes and then synchronises results at
an ``EvidenceAggregator`` node. Judges and synthesis are planned for later
phases.

## Project Structure

- ``src/state.py`` – Pydantic/TypedDict definitions for state and evidence
- ``src/tools`` – sandboxed repo and PDF tools
- ``src/nodes/detectives.py`` – detective agent functions
- ``src/graph.py`` – graph builder used by tests
- ``tests/`` – unit tests for Phase 1/2 functionality

Additional deliverables (judges, justice, final reports, etc.) will appear in
later phases.

