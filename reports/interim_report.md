# Interim Report – Automaton Auditor (Phase 2)

## Architecture Decision Rationale

### 1. Typed State with Pydantic/TypedDict
We chose Pydantic models combined with a `TypedDict`-wrapped state container because
parallel agents must update shared data without stepping on each other. Plain dicts
would allow conflicting writes: one detective could overwrite another's evidence list.
Pydantic enforces field types and allows us to document each field; `Annotated` reducers
(`operator.add`, `operator.ior`) define merge semantics declaratively. The alternative
was using `dataclasses` or plain dicts, but dataclasses lack runtime validation and
deriving merge behavior is manual. TypedDict+Pydantic hits the sweet spot of
strictness and flexibility. The cost is additional boilerplate and dependency on
the pydantic library, but those trade‑offs are acceptable for the reliability gains.

### 2. AST Parsing for Graph Structure
Regex-based scanning is brittle: it fails on multiline calls, comments, or when the
StateGraph object is imported under an alias. To robustly detect `StateGraph`
instantiation and edge additions, we implemented an `ast.NodeVisitor` that inspects
`ast.Call` nodes. This approach handles nested constructs and future language
extensions without modification. We considered using the `gitingest` package or
`tree‑sitter`, but they add heavy dependencies; the built-in `ast` module is
lightweight and sufficient for our limited needs. The primary risk mitigated is
false negatives/positives in forensic checks, which would undermine the detector
agents' credibility.

### 3. Sandbox Strategy for Git Clones
Cloning arbitrary repositories poses security and pollution risks. The tool uses
`tempfile.TemporaryDirectory()` to create an isolated workspace; the path is
passed to `subprocess.run(['git','clone','--depth','10',...])`. We capture stderr,
check return codes, and clean up the tempdir on failure. An alternative would have
been to execute `git` in the current working directory or use `os.system()`, both
of which can inject files into the host workspace and have no error feedback. The
temporary directory approach costs a tiny bit of disk I/O but ensures safety and
easy cleanup.

### 4. RAG‑Lite PDF Ingestion
The PDF parsing tool uses `pypdf` for text and optionally `pymupdf` for images. We
avoid loading the entire document into an LLM context; instead tests simply extract
full text, leaving room to implement chunking or retrieval-as-needed later. The
trade‑off is simplicity today versus optimal performance on large reports later. We
chose this lean design because the rubric requires only evidence extraction, not
full question-answering.

## Gap Analysis and Forward Plan

Phase 2 delivered the detective layer; the judicial and synthesis layers remain.
Major unfinished components:

* **Judge Nodes** currently absent. Only detective nodes exist; there are no
  `Prosecutor`, `Defense`, or `TechLead` implementations, nor any structured LLM
  calls. The plan is to add them in Phase 3 with `.with_structured_output(JudicialOpinion)`
  and persona-specific system prompts loaded from `rubric.json`.
* **Chief Justice Synthesis** is stubbed as a simple average; no hardcoded rules or
  dissent summaries exist. Phase 4 will implement deterministic conflict-resolution
  (security override, fact supremacy, variance re-evaluation) and serialize to a
  Markdown report.
* **EvidenceAggregator** currently just returns the state. Later, it should verify
  completeness and route to judges or error paths if key evidence is missing.
* **VisionInspector** remains a stub; image analysis will require multimodal models
  and OCR/vision pipelines.

Concrete next steps:

1. Create judge node templates that enforce schema and retry on parse errors.
   - Risk: LLMs may ignore persona prompts and produce similar output; mitigate by
     embedding explicit instructions and quality checks on returned `judge` field.
2. Extend the graph builder with fan‑out/fan‑in for judges and conditional edges
   (e.g. `EvidenceAggregator` -> `ErrorHandler` if `state.evidences` empty).
3. Develop `ChiefJusticeNode.synthesize()` rules based on the `synthesis_rules`
   section of `rubric.json`, including variance-triggered re-evaluation.
   - Risk: Complexity in implementing the variance logic; start with a simple
     loop scanning for score spread >2.
4. Add unit tests verifying judge parallelism and the deterministic synthesis rules
   once implemented.

Identified failure modes:
- LLM judges might return unparseable text → must add fallback/retry logic.
- The stubbed graph may silently swallow missing evidence; add explicit state
  validation.

## StateGraph Architecture Diagram

(See attached image **interim_graph.png** in the final PDF – placeholder below.)

```
START
  │
  ├─► RepoInvestigator ──┐
  ├─► DocAnalyst   ──────┤
  └─► VisionInspector ───┼─► EvidenceAggregator ──► (future Judge fan-out)
                          │
                          └─► (error handling)
```

*Detectives fan out from `START` and converge at `EvidenceAggregator`. The graph
shows evidence objects flowing along edges. Conditional edge (arrow to
error handler) denotes missing artifact handling. In Phase 3 the judges will fan
out from `EvidenceAggregator` to `Prosecutor`, `Defense`, and `TechLead` before
rejoining at `ChiefJustice`.*


---

*This interim report documents decisions taken and outlines a clear plan for the
remaining layers. It will be converted to PDF and committed so peers can access
it during the audit process.*
