from postarr import db


class CurrentJobs(db.Model):
    __tablename__ = "current_jobs"
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String, nullable=True)
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True)


class JobHistory(db.Model):
    __tablename__ = "job_history"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String, nullable=True)
    job_name = db.Column(db.String, nullable=True)
    run_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String, nullable=True)
    run_type = db.Column(db.String, nullable=True)
    message = db.Column(db.String, nullable=True)
