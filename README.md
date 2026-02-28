# automaton-auditor
[![CI](https://github.com/ruthasoll/automaton-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/ruthasoll/automaton-auditor/actions/workflows/ci.yml)

A Week 2 Automaton Auditor skeleton. This repository implements Phase 1, 2, 3, and 4:
- typed state models
- safe forensic tools
- detective nodes and precise evidence extraction
- parallel judge nodes with distinct personas (Prosecutor, Defense, TechLead)
- deterministic Chief Justice synthesis engine
- graph orchestration for the entire workflow

## Setup

1. Clone the repository and create a Python 3.12 environment (`uv` is used throughout but any venv/conda works):

   ```bash
   git clone <repo-url>
   cd automaton-auditor
   uv env use python@3.12
   uv install
   ```

2. Copy `.env.example` to `.env` and populate API keys:

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

## Running the Automaton Auditor Swarm

With all phases implemented, you can execute the full Digital Courtroom graph. Run the following command:

```bash
uv sync
python src/graph.py --repo <github-repo-url> --pdf <path-to-pdf> --output audit/report.md
```

This will:
1. Orchestrate the parallel **Detectives** to collect evidence.
2. Synchronize findings via `EvidenceAggregator`.
3. Fan-out to the **Judicial Layer** (`Prosecutor`, `Defense`, `TechLead`) where personas evaluate criteria in parallel.
4. Pass opinions to the **Chief Justice Node** for final synthesis and resolution.
5. Save the final Markdown verdict to `audit/report.md` (or the path you specified).

### Using Docker (Containerized Runtime)

For full isolation, you can build and run the auditor as a Docker container:

```bash
docker build -t automaton-auditor .
docker run --rm --env-file .env -v $(pwd)/audit:/app/audit automaton-auditor --repo <github-repo-url> --pdf <path-to-pdf>
```

## Project Structure


- `src/state.py` – Pydantic/TypedDict definitions for state, evidence, opinions, and reports
- `src/tools/` – sandboxed repo and PDF extraction tools
- `src/nodes/detectives.py` – forensic analyst nodes (`RepoInvestigator`, `DocAnalyst`)
- `src/nodes/judges.py` – conflicting LLM personas (`Prosecutor`, `Defense`, `TechLead`)
- `src/nodes/justice.py` – deterministic rules engine (`ChiefJusticeNode`)
- `src/graph.py` – complete LangGraph builder and CLI entrypoint
- `tests/` – unit tests for early phase functionality
