import pytest

from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server


def test_queue_returns_jobs_in_arrival_order() -> None:
    queue = JobQueue()

    first_job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
    )

    second_job = Job(
        job_id="job-2",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=5,
    )

    queue.add(first_job)
    queue.add(second_job)

    # Bakmak, görevi kuyruktan çıkarmamalı.
    assert queue.peek() is first_job
    assert len(queue.jobs) == 2

    # Görevler eklendikleri sırayla çıkmalı.
    assert queue.pop_next() is first_job
    assert queue.peek() is second_job
    assert queue.pop_next() is second_job

    # Boş kuyrukta görev bulunmaz.
    assert queue.peek() is None
    assert queue.pop_next() is None


def test_queue_rejects_duplicate_job_id() -> None:
    queue = JobQueue()

    first_job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
    )

    duplicate_job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=5,
    )

    queue.add(first_job)

    with pytest.raises(ValueError, match="Job ID already exists in queue"):
        queue.add(duplicate_job)

    assert len(queue.jobs) == 1
    assert queue.peek() is first_job


def test_queue_rejects_running_job() -> None:
    queue = JobQueue()

    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
    )

    server.allocate(job)

    with pytest.raises(ValueError, match="Only waiting jobs can be queued"):
        queue.add(job)

    assert queue.jobs == []