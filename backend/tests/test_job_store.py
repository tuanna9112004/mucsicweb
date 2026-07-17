from pathlib import Path

from app.core.job_models import Job, JobStatus
from app.core.job_store import JobStore


def _make_job(job_id: str, status: JobStatus = JobStatus.UPLOADED) -> Job:
    return Job(
        job_id=job_id,
        original_filename=f"{job_id}.mp3",
        source_path=Path(f"/tmp/{job_id}/source.mp3"),
        work_dir=Path(f"/tmp/{job_id}"),
        status=status,
    )


def test_two_jobs_do_not_overwrite_each_other():
    store = JobStore()
    job_a = _make_job("job-a")
    job_b = _make_job("job-b")

    store.add(job_a)
    store.add(job_b)

    assert store.get("job-a") is job_a
    assert store.get("job-b") is job_b
    assert store.get("job-a").original_filename == "job-a.mp3"
    assert store.get("job-b").original_filename == "job-b.mp3"


def test_new_job_does_not_overwrite_running_job():
    store = JobStore()
    running_job = _make_job("running", status=JobStatus.RUNNING)
    store.add(running_job)

    new_job = _make_job("new-upload")
    store.add(new_job)

    assert store.get("running").status == JobStatus.RUNNING
    assert store.get("new-upload") is new_job


def test_has_running_job_detects_running_status():
    store = JobStore()
    store.add(_make_job("idle", status=JobStatus.UPLOADED))

    assert store.has_running_job() is False

    store.add(_make_job("busy", status=JobStatus.RUNNING))

    assert store.has_running_job() is True


def test_has_running_job_excludes_given_job_id():
    store = JobStore()
    store.add(_make_job("self", status=JobStatus.RUNNING))

    assert store.has_running_job(exclude_job_id="self") is False


def test_unknown_job_id_returns_none():
    store = JobStore()

    assert store.get("does-not-exist") is None
