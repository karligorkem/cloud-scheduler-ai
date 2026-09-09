from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.server import Server


def test_allocate_reserves_resources_and_starts_job() -> None:
    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
        gpu_count=2,
    )

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=5,
        required_gpu_count=1,
    )

    server.allocate(job)

    assert server.available_cpu == 6
    assert server.available_memory_gb == 12.0
    assert server.available_gpu_count == 1
    assert job.status == JobStatus.RUNNING
    assert job.assigned_server_id == "server-1"
    assert job.remaining_steps == 5