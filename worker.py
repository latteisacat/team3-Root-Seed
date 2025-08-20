from models import db, Job, Event
from agent import run_pipeline, log

def run_job(job_id):
    job = Job.query.get(job_id)
    job.status = "RUNNING"; job.progress = 10; db.session.commit()
    try:
        log(job_id, "stage", "PREPARE")
        findings = run_pipeline(job)
        job.status = "DONE"; job.progress = 100; db.session.commit()
        log(job_id, "done", "Job completed", {"findings": [f.control_id for f in findings]})
    except Exception as e:
        job.status = "FAILED"; db.session.commit()
        log(job_id, "error", "Job failed", {"error": str(e)})
