from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import JSON

db = SQLAlchemy()

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String, nullable=False)
    controls = db.Column(JSON, default=list)
    ike_patches = db.Column(JSON, default=list)
    depth = db.Column(db.String, default="safe")
    status = db.Column(db.String, default="QUEUED")
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "target": self.target, "controls": self.controls,
            "ike_patches": self.ike_patches, "depth": self.depth,
            "status": self.status, "progress": self.progress,
            "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat()
        }

    @staticmethod
    def from_request(data):
        job = Job(
            target=data.get("target"),
            controls=data.get("controls", []),
            ike_patches=data.get("ike_patches", []),
            depth=data.get("depth", "safe"),
            status="QUEUED",
            progress=0
        )
        return job

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String, default="info")
    message = db.Column(db.String, default="")
    payload_json = db.Column(JSON, default=dict)

    def to_json(self):
        return {
            "id": self.id, "job_id": self.job_id, "ts": self.ts.isoformat(),
            "level": self.level, "message": self.message, "payload": self.payload_json
        }

class Artifact(db.Model):
    __tablename__ = "artifacts"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    type = db.Column(db.String, default="json")
    ref = db.Column(db.String, default="")
    sha256 = db.Column(db.String, default="")
    meta_json = db.Column(JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Finding(db.Model):
    __tablename__ = "findings"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    control_id = db.Column(db.String, nullable=False)
    status = db.Column(db.String, default="unknown")  # pass/partial/fail/unknown
    evidence_refs = db.Column(JSON, default=list)
    finding = db.Column(db.String, default="")
    risk = db.Column(db.String, default="")
    recommendation = db.Column(db.String, default="")
    repro = db.Column(JSON, default=list)
    raw = db.Column(JSON, default=dict)
