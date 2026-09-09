import pytest

from cloud_scheduler.domain.job import Job, JobStatus


def test_job_starts_in_waiting_status() -> None:
    job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=10,
    )

    assert job.job_id == "job-1"
    assert job.status == JobStatus.WAITING
    assert job.assigned_server_id is None


def test_job_starts_with_all_duration_remaining() -> None:
    job = Job(
        job_id="job-2",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=5,
        priority=3,
        required_gpu_count=1,
    )

    assert job.job_id == "job-2"
    assert job.required_cpu == 2
    assert job.required_memory_gb == 4.0
    assert job.required_gpu_count == 1
    assert job.duration_steps == 5
    assert job.remaining_steps == 5
    assert job.priority == 3


def test_job_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="Job ID cannot be empty"):
        Job(
            job_id="   ",
            required_cpu=4,
            required_memory_gb=8.0,
            duration_steps=10,
        )


def test_job_rejects_zero_cpu() -> None:
    with pytest.raises(ValueError, match="Required CPU must be greater than zero"):
        Job(
            job_id="job-1",
            required_cpu=0,
            required_memory_gb=8.0,
            duration_steps=10,
        )


def test_job_rejects_negative_memory() -> None:
    with pytest.raises(ValueError, match="Required memory must be greater than zero"):
        Job(
            job_id="job-1",
            required_cpu=4,
            required_memory_gb=-8.0,
            duration_steps=10,
        )


def test_job_rejects_zero_duration() -> None:
    with pytest.raises(ValueError, match="Duration steps must be greater than zero"):
        Job(
            job_id="job-1",
            required_cpu=4,
            required_memory_gb=8.0,
            duration_steps=0,
        )


def test_job_rejects_invalid_priority() -> None:
    with pytest.raises(ValueError, match="Priority must be between 1 and 5"):
        Job(
            job_id="job-1",
            required_cpu=4,
            required_memory_gb=8.0,
            duration_steps=10,
            priority=6,
        )


def test_job_rejects_negative_gpu_requirement() -> None:
    with pytest.raises(ValueError, match="Required GPU count cannot be negative"):
        Job(
            job_id="job-1",
            required_cpu=4,
            required_memory_gb=8.0,
            duration_steps=10,
            required_gpu_count=-1,
        )


def test_job_removes_spaces_from_id() -> None:
    job = Job(
        job_id="  job-1  ",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=10,
    )

    assert job.job_id == "job-1"