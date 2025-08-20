# llm_client.py
import os, json
from typing import List, Dict
from openai import OpenAI

USE_GPT = os.getenv("USE_GPT", "false").lower() == "true"
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-5-mini")

_client = None  # lazy

def _get_client():
    global _client
    if _client is not None:
        return _client
    if not USE_GPT:
        return None
    from openai import OpenAI  # 지연 import
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    _client = OpenAI()
    return _client

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "http_check",
            "description": "Fetch HTTP(S) response headers and status from a target URL",
            "parameters": {
                "type":"object",
                "properties": {"url":{"type":"string"}},
                "required":["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_exec",
            "description": "Execute a read-only command via SSH on a target host",
            "parameters": {
                "type":"object",
                "properties": {"cmd":{"type":"string"}},
                "required":["cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mariadb_query",
            "description": "Run a read-only SQL query on MariaDB",
            "parameters": {
                "type":"object",
                "properties": {"sql":{"type":"string"}},
                "required":["sql"]
            }
        }
    }
]

DECISION_SCHEMA = {
    "name":"decision",
    "schema":{
        "type":"object",
        "properties":{
            "items":{"type":"array","items":{
                "type":"object",
                "properties":{
                    "control_id":{"type":"string"},
                    "status":{"type":"string","enum":["pass","partial","fail","unknown"]},
                    "evidence_refs":{"type":"array","items":{"type":"string"}},
                    "finding":{"type":"string"},
                    "risk":{"type":"string"},
                    "recommendation":{"type":"string"},
                    "repro":{"type":"array","items":{"type":"string"}}
                },
                "required":["control_id","status","evidence_refs","recommendation","repro"]
            }},
            "summary":{"type":"object","properties":{
                "pass":{"type":"integer"},
                "fail":{"type":"integer"},
                "na":{"type":"integer"},
                "unknown":{"type":"integer"}
            }}
        },
        "required":["items","summary"],
        "additionalProperties": False
    },
    "strict": True
}

SYSTEM = """You are a security check operator. 
- Plan tool calls using provided controls/RAG. 
- Use tools to collect evidence before deciding. 
- Output only valid structured JSON per schema (no extra fields). 
- If evidence is missing, mark 'unknown' and propose next steps."""

def plan_steps_with_llm(target: str, controls: Dict[str, Dict]) -> List[Dict]:
    """
    GPT에게 어떤 툴을 어떤 인자로 호출할지 계획시킴.
    반환: [{"tool":"http_check","args":{"url":target}}, ...]
    """
    if not USE_GPT:
        # fallback: U31/U32/U33 → http_check만
        steps = []
        for cid, c in controls.items():
            if any(k in c.get("check","").lower() for k in ["hsts","csp","x-frame","frame-ancestors"]):
                steps.append({"tool":"http_check","args":{"url": target}})
        return steps

    client = _get_client()

    user = {
        "role":"user",
        "content": json.dumps({
            "task":"plan",
            "target": target,
            "controls": controls
        }, ensure_ascii=False)
    }
    resp = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role":"system","content": SYSTEM}, user],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0
    )
    steps = []
    for c in resp.choices:
        tc = c.message.tool_calls or []
        for t in tc:
            steps.append({"tool": t.function.name, "args": json.loads(t.function.arguments or "{}")})
    return steps

def decide_with_llm(evidence: List[Dict], controls: Dict[str, Dict]) -> Dict:
    """
    GPT에게 구조화 출력 스키마로 판정.
    evidence: [{"tool":"http_check","result":{...},"sha256":"..."}]
    """
    if not USE_GPT:
        # 로컬 규칙: HSTS/CSP/XFO 간단 판정
        items = []; summary = {"pass":0,"fail":0,"na":0,"unknown":0}
        hdrs = {}
        for ev in evidence:
            if ev.get("tool")=="http_check":
                for k,v in ev["result"].get("headers", {}).items():
                    hdrs[k.lower()] = v
        for cid, c in controls.items():
            if cid.upper()=="U31":
                ok = "strict-transport-security" in hdrs
                st = "pass" if ok else "fail"
                items.append({"control_id":cid,"status":st,"evidence_refs":[],
                              "finding":"HSTS present" if ok else "HSTS missing",
                              "risk": "" if ok else "Downgrade/SSL stripping risk",
                              "recommendation":"Add HSTS header",
                              "repro":["curl -I "+evidence[0]["result"].get("url","")]})
                summary[st]+=1
            elif cid.upper()=="U32":
                ok = "content-security-policy" in hdrs
                st = "pass" if ok else "fail"
                items.append({"control_id":cid,"status":st,"evidence_refs":[],
                              "finding":"CSP present" if ok else "CSP missing",
                              "risk": "" if ok else "XSS/MiTM risk",
                              "recommendation":"Add CSP with strict directives",
                              "repro":["curl -I "+evidence[0]["result"].get("url","")]})
                summary[st]+=1
            elif cid.upper()=="U33":
                ok = ("x-frame-options" in hdrs) or \
                     ("content-security-policy" in hdrs and "frame-ancestors" in hdrs.get("content-security-policy","").lower())
                st = "pass" if ok else "fail"
                items.append({"control_id":cid,"status":st,"evidence_refs":[],
                              "finding":"Clickjacking protection present" if ok else "No clickjacking protection",
                              "risk": "" if ok else "UI redress attack risk",
                              "recommendation":"Set CSP frame-ancestors or X-Frame-Options",
                              "repro":["curl -I "+evidence[0]["result"].get("url","")]})
                summary[st]+=1
            else:
                items.append({"control_id":cid,"status":"unknown","evidence_refs":[],
                              "finding":"No rule","risk":"","recommendation":"Add rule","repro":[]})
                summary["unknown"]+=1
        return {"items":items, "summary":summary}
    
    client = _get_client()

    # GPT 사용 경로: Structured Output
    msgs = [{"role":"system","content": SYSTEM}]
    msgs.append({"role":"user","content": json.dumps({
        "task":"decide",
        "controls": controls,
        "evidence": evidence
    }, ensure_ascii=False)})

    resp = client.chat.completions.parse(
        model=GPT_MODEL,
        messages=msgs,
        response_format=DECISION_SCHEMA,
        temperature=0
    )
    return resp.choices[0].message.parsed  # dict
