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

    # AST-based checks
    
    # 1. State Management Rigor (src/state.py)
    state_file = repo_path / "src" / "state.py"
    if state_file.exists():
        try:
            content = state_file.read_text(encoding="utf-8")
            from ast import parse
            tree = parse(content)
            
            # Simple AST visitor for State classes
            has_pydantic = "BaseModel" in content
            has_reducers = "operator.add" in content or "operator.ior" in content
            found = has_pydantic and has_reducers
            
            evidences["state_management_rigor"] = [Evidence(
                goal="State Management Rigor",
                found=found,
                content="Contains BaseModel and operator reducers" if found else "Missing strict typing or reducers",
                location=str(state_file),
                rationale="AST string check shows required components",
                confidence=0.85
            )]
        except Exception as e:
            evidences["state_management_rigor"] = [Evidence(
                goal="State Management Rigor",
                found=False,
                location=str(state_file),
                rationale=f"Failed to parse state.py: {e}",
                confidence=0.1
            )]
    else:
        evidences["state_management_rigor"] = [Evidence(
            goal="State Management Rigor",
            found=False,
            location="src/state.py",
            rationale="File does not exist",
            confidence=1.0
        )]

    # 2. Graph Orchestration (src/graph.py)
    graph_file = repo_path / "src" / "graph.py"
    if graph_file.exists():
        try:
            content = graph_file.read_text(encoding="utf-8")
            struct = repo_tools.analyze_graph_structure(content)
            
            found = struct["found_stategraph"] and struct["fan_out_from_start"] and struct["has_aggregator"] and struct["has_conditional"]
            
            summary = (f"Nodes: {struct['nodes']}\n"
                       f"Fan-out: {struct['fan_out_from_start']}\n"
                       f"Aggregator: {struct['has_aggregator']}\n"
                       f"Conditional Edges: {struct['has_conditional']}")
                       
            evidences["graph_orchestration"] = [Evidence(
                goal="Graph Orchestration Architecture",
                found=found,
                content=summary,
                location=str(graph_file),
                rationale="GraphASTAnalyzer verified node structure and parallel fan-out",
                confidence=0.95 if found else 0.8
            )]
        except Exception as e:
            evidences["graph_orchestration"] = [Evidence(
                goal="Graph Orchestration Architecture",
                found=False,
                location=str(graph_file),
                rationale=f"Failed to analyze graph structure: {e}",
                confidence=0.1
            )]
    else:
        evidences["graph_orchestration"] = [Evidence(
            goal="Graph Orchestration Architecture",
            found=False,
            location="src/graph.py",
            rationale="File does not exist",
            confidence=1.0
        )]

    # 3. Safe Tool Engineering
    tools_dir = repo_path / "src" / "tools"
    if tools_dir.exists():
        has_tempfile = False
        has_os_system = False
        target_file = ""
        for tool_file in tools_dir.glob("*.py"):
            content = tool_file.read_text(encoding="utf-8")
            if "tempfile" in content:
                has_tempfile = True
                target_file = str(tool_file)
            if "os.system" in content:
                has_os_system = True
                target_file = str(tool_file)
                
        found = has_tempfile and not has_os_system
        evidences["safe_tool_engineering"] = [Evidence(
            goal="Safe Tool Engineering",
            found=found,
            content="Tempfile isolation used" if found else ("Found os.system" if has_os_system else "No temp isolation"),
            location=target_file if target_file else "src/tools/",
            rationale="Ast/text search for tool safety parameters",
            confidence=0.9
        )]
    else:
         evidences["safe_tool_engineering"] = [Evidence(
            goal="Safe Tool Engineering",
            found=False,
            location="src/tools/",
            rationale="Tools directory does not exist",
            confidence=1.0
        )]

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
    """Multimodal detective – visualizes workflow diagrams."""
    evidences: Dict[str, List[Evidence]] = {}
    
    # We first see if DocAnalyst extracted any images
    gen_evs = state.get("evidences", {}).get("swarm_visual", [])
    has_images = False
    
    if gen_evs:
        for ev in gen_evs:
            if "images extracted" in str(ev.content):
                has_images = True
                break
                
    pdf_path_str = state.get("pdf_path", "")
    pdf_path = Path(pdf_path_str) if pdf_path_str else None
    
    # This is slightly redundant but DocAnalyst cleans up its temp_dir. 
    # We will re-extract here specifically for the VisionInspector to send.
    if pdf_path and pdf_path.exists() and has_images:
        pdf_data = doc_tools.extract_pdf_content(pdf_path)
        images = pdf_data.get("image_paths", [])
        
        if images:
            try:
                import base64
                from langchain_core.messages import HumanMessage
                from langchain_openai import ChatOpenAI
                
                llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
                
                # Take the first image (usually the architecture diagram if there are few)
                target_img = images[0]
                with open(target_img, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    
                msg = HumanMessage(
                    content=[
                        {"type": "text", "text": "Analyze this architectural diagram. Is it a LangGraph State Machine diagram showing parallel branching for Detectives and Judges (with EvidenceAggregator in between), or just a generic flowchart? Reply ONLY with 'CLASSIFICATION: [classification]. FLOW: [brief description]'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}
                    ]
                )
                
                response = llm.invoke([msg])
                content_str = str(response.content)
                
                is_parallel = "parallel" in content_str.lower() or "stategraph" in content_str.lower()
                
                evidences["swarm_visual"] = [Evidence(
                    goal="Architectural Diagram Analysis",
                    found=is_parallel,
                    content=content_str,
                    location=str(pdf_path) + " (Image 1)",
                    rationale="Vision model analyzed the diagram for parallel fan-out architecture",
                    confidence=0.9
                )]
            except Exception as e:
                evidences["swarm_visual"] = [Evidence(
                    goal="Architectural Diagram Analysis",
                    found=False,
                    location=str(pdf_path),
                    rationale=f"Vision model failed: {e}",
                    confidence=0.1
                )]
            finally:
                doc_tools.cleanup_pdf_temp_dir(pdf_data.get("temp_dir"))
        else:
             evidences["swarm_visual"] = [Evidence(
                goal="Architectural Diagram Analysis",
                found=False,
                location=str(pdf_path),
                rationale="No images actually extracted",
                confidence=1.0
            )]
    else:
        evidences["swarm_visual"] = [Evidence(
            goal="Architectural Diagram Analysis",
            found=False,
            location="",
            rationale="No diagram provided or extracted",
            confidence=1.0
        )]

    return evidences