from flask import Flask, request, jsonify, Response, send_file, render_template, redirect, url_for
from models import db, Job, Event, Artifact, Finding
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, DEFAULT_TARGET
from rq import Queue
from redis import Redis
from worker import run_job
import time, json
from report import build_pdf
import os, tempfile

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
db.init_app(app)

redis = Redis.from_url("redis://localhost:6379/0")
q = Queue("jobs", connection=redis)

@app.cli.command("db_init")
def db_init():
    with app.app_context():
        db.create_all()
        print("DB initialized.")

@app.route("/")
def dashboard():
    jobs = Job.query.order_by(Job.created_at.desc()).limit(20).all()
    return render_template("dashboard.html", jobs=jobs, default_target=DEFAULT_TARGET)

@app.post("/api/jobs")
def create_job():
    data = request.get_json()
    if not data.get("target"):
        return jsonify({"error":"target required"}), 400
    job = Job.from_request(data)
    db.session.add(job); db.session.commit()
    rq_job = q.enqueue(run_job, job.id)
    return jsonify({"job_id": job.id, "rq_id": rq_job.id})

@app.get("/api/jobs")
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return jsonify([j.to_dict() for j in jobs])

@app.get("/api/jobs/<jid>")
def get_job(jid):
    job = Job.query.get_or_404(jid)
    return jsonify(job.to_dict())

@app.get("/api/jobs/<jid>/stream")
def stream(jid):
    def gen():
        last_id = 0
        while True:
            events = (Event.query
                      .filter(Event.job_id==jid, Event.id>last_id)
                      .order_by(Event.id.asc()).all())
            for e in events:
                last_id = e.id
                yield f"event: {e.level}\ndata: {json.dumps(e.to_json(), ensure_ascii=False)}\n\n"
            time.sleep(1)
    return Response(gen(), mimetype="text/event-stream")

@app.get("/jobs/<jid>")
def job_detail(jid):
    job = Job.query.get_or_404(jid)
    findings = Finding.query.filter_by(job_id=jid).all()
    artifacts = Artifact.query.filter_by(job_id=jid).all()
    return render_template("job.html", job=job, findings=findings, artifacts=artifacts)

@app.post("/web/new_job")
def web_new_job():
    target = request.form.get("target") or DEFAULT_TARGET
    controls = [c.strip() for c in (request.form.get("controls") or "U31").split(",") if c.strip()]
    data = {"target": target, "controls": controls, "ike_patches": [], "depth": "safe"}
    job = Job.from_request(data)
    db.session.add(job); db.session.commit()
    q.enqueue(run_job, job.id)
    return redirect(url_for("job_detail", jid=job.id))

@app.get("/api/jobs/<jid>/report.json")
def report_json(jid):
    findings = Finding.query.filter_by(job_id=jid).all()
    items = []
    summary = {"pass":0,"fail":0,"na":0,"unknown":0}
    for f in findings:
        items.append(f.raw)
        summary[f.status] = summary.get(f.status,0)+1
    return jsonify({"items": items, "summary": summary})

@app.get("/api/jobs/<jid>/report.pdf")
def report_pdf(jid):
    job = Job.query.get_or_404(jid)
    findings = Finding.query.filter_by(job_id=jid).all()
    summary = {"pass":0,"fail":0,"na":0,"unknown":0}
    for f in findings: summary[f.status] = summary.get(f.status,0)+1
    meta = {"Target": job.target, "Controls": ",".join(job.controls), "JobID": str(job.id)}
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    build_pdf(tmp.name, "Security Check Report", meta, findings, summary)
    return send_file(tmp.name, as_attachment=True, download_name=f"job_{job.id}_report.pdf")
