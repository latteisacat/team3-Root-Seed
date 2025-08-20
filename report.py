# report.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

def build_pdf(path: str, title: str, meta: dict, findings: list, summary: dict):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, title); y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Generated: {datetime.utcnow().isoformat()}Z"); y -= 14
    for k,v in meta.items():
        c.drawString(40, y, f"{k}: {v}"); y -= 12
    y -= 10
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Summary"); y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"PASS: {summary.get('pass',0)}  FAIL: {summary.get('fail',0)}  UNKNOWN: {summary.get('unknown',0)}")
    y -= 18
    c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Findings"); y -= 16
    c.setFont("Helvetica", 10)
    for f in findings:
        block = f"[{f.control_id}] {f.status.upper()} - {f.finding}"
        for line in _wrap(block, 90):
            c.drawString(40, y, line); y -= 12
        c.drawString(40, y, "  Recommendation: " + f.recommendation[:1000]); y -= 14
        if y < 100: c.showPage(); y = h - 40; c.setFont("Helvetica", 10)
    c.showPage(); c.save()

def _wrap(text, width):
    words = text.split()
    line = []
    for w in words:
        line.append(w)
        if len(" ".join(line)) > width:
            yield " ".join(line); line = []
    if line: yield " ".join(line)
