# rag.py
import os, re, glob
from dataclasses import dataclass
from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOC_DIR = os.getenv("RAG_DOC_DIR", "docs")

@dataclass
class Snippet:
    path: str
    text: str
    score: float

def _load_docs():
    paths = glob.glob(os.path.join(DOC_DIR, "**/*.*"), recursive=True)
    items = []
    for p in paths:
        if any(p.lower().endswith(ext) for ext in (".md", ".txt")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    items.append((p, f.read()))
            except Exception:
                pass
    return items

def search(query: str, k: int = 3) -> List[Snippet]:
    docs = _load_docs()
    if not docs:
        return []
    texts = [t for _, t in docs]
    vec = TfidfVectorizer(max_features=8000).fit(texts + [query])
    qv = vec.transform([query])
    dv = vec.transform(texts)
    sims = cosine_similarity(qv, dv)[0]
    ranked = sorted(list(enumerate(sims)), key=lambda x: x[1], reverse=True)[:k]
    out = []
    for idx, score in ranked:
        out.append(Snippet(path=docs[idx][0], text=texts[idx], score=float(score)))
    return out

def control_snippets(control_id: str) -> Dict:
    """
    control_id(U31/U32/U33 등)에 대한 간단 매핑 + RAG 보강.
    """
    base = {
        "U31": {
            "title": "U31: HSTS header required",
            "check": "Make an HTTPS request and verify Strict-Transport-Security header exists.",
            "standard": "HSTS must be present for public endpoints (min 6 months).",
            "improvement": "Enable HSTS on the web server config."
        },
        "U32": {
            "title": "U32: Content-Security-Policy required",
            "check": "Check response has Content-Security-Policy header with safe directives.",
            "standard": "CSP must restrict scripts/styles to trusted origins.",
            "improvement": "Add CSP header; avoid unsafe-inline unless nonce/hash used."
        },
        "U33": {
            "title": "U33: Clickjacking protection",
            "check": "Check frame-ancestors via CSP or X-Frame-Options set properly.",
            "standard": "Use CSP frame-ancestors 'none' or specific allowlist; XFO SAMEORIGIN optional.",
            "improvement": "Prefer CSP frame-ancestors; remove ALLOW-FROM legacy."
        }
    }
    c = base.get(control_id.upper(), {"title": control_id, "check":"N/A","standard":"","improvement":""})
    # RAG 보강: control_id로 검색해서 상위 스니펫 일부만 붙임
    hits = search(control_id)
    if hits:
        c["rag_support"] = [{"path": h.path, "score": h.score, "excerpt": h.text[:600]} for h in hits]
    return c
