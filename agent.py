# agent.py
from models import db, Event, Artifact, Finding
from mcp_bridge import http_check, ssh_exec, mariadb_query
from rag import control_snippets
from llm_client import plan_steps_with_llm, decide_with_llm
import json

def log(job_id, level, message, payload=None):
    ev = Event(job_id=job_id, level=level, message=message, payload_json=payload or {})
    db.session.add(ev); db.session.commit()

def run_pipeline(job):
    artifacts_db = []
    # 1) RAG
    log(job.id, "stage", "RAG")
    controls = {cid: control_snippets(cid) for cid in job.controls}

    # 2) PLAN (LLM or fallback)
    log(job.id, "stage", "PLAN")
    plan = plan_steps_with_llm(job.target, controls)
    if not plan:
        log(job.id, "warn", "No plan produced; marking unknown")
    # 3) EXECUTE
    for st in plan:
        log(job.id, "info", "tool_call", {"tool": st["tool"], "args": st["args"]})
        if st["tool"] == "http_check":
            out = http_check(st["args"]["url"])
        elif st["tool"] == "ssh_exec":
            out = ssh_exec(st["args"]["cmd"])
        elif st["tool"] == "mariadb_query":
            out = mariadb_query(st["args"]["sql"])
        else:
            out = {"tool": st["tool"], "args": st["args"], "result": {"note":"unknown tool"}, "sha256": ""}
        art = Artifact(job_id=job.id, type="json", ref="", sha256=out["sha256"],
                       meta_json={**out["result"], "tool": out["tool"]})
        db.session.add(art); db.session.commit()
        artifacts_db.append(art)
        log(job.id, "info", "tool_done", {"tool": out["tool"], "sha256": out["sha256"]})

    # evidence list for LLM
    evidence = []
    for a in artifacts_db:
        d = dict(a.meta_json)
        evidence.append({"tool": d.get("tool"), "result": d, "sha256": a.sha256})

    # 4) ANALYZE (LLM structured decision or fallback)
    log(job.id, "stage", "ANALYZE")
    decision = decide_with_llm(evidence, controls)
    items = decision.get("items", [])
    findings = []
    for it in items:
        f = Finding(job_id=job.id,
                    control_id=it.get("control_id"),
                    status=it.get("status","unknown"),
                    evidence_refs=it.get("evidence_refs",[]),
                    finding=it.get("finding",""),
                    risk=it.get("risk",""),
                    recommendation=it.get("recommendation",""),
                    repro=it.get("repro",[]),
                    raw=it)
        db.session.add(f); db.session.commit()
        findings.append(f)

    # 5) REPORT
    log(job.id, "stage", "REPORT")
    return findings
