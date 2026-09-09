from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.server import Server
def test_server_rejects_job_when_memory_is_insufficient() -> None:
    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=4.0,
    )

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=8.0,
        duration_steps=5,
    )

    result = server.can_host(job)

    assert result is False
def test_server_rejects_job_when_gpu_is_insufficient() -> None:
    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
        gpu_count=0,
    )

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=5,
        required_gpu_count=1,
    )

    result = server.can_host(job)

    assert result is False
def test_inactive_server_rejects_job() -> None:
    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    server.is_active = False

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=5,
    )

    result = server.can_host(job)

    assert result is False

def test_server_rejects_running_job() -> None:

    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=5,
    )

    job.status = JobStatus.RUNNING

    result = server.can_host(job)

    assert result is False
def test_server_rejects_already_assigned_job() -> None:
    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=5,
    )

    job.assigned_server_id = "server-2"

    result = server.can_host(job)

    assert result is False
def test_server_accepts_job_that_exactly_fits() -> None:
    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
        gpu_count=1,
    )

    job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=5,
        required_gpu_count=1,
    )

    result = server.can_host(job)

    assert result is True

    # Kontrol etmek kaynakları tüketmemelidir.
    assert server.available_cpu == 4
    assert server.available_memory_gb == 8.0
    assert server.available_gpu_count == 1

    # Görev henüz başlatılmamıştır.
    assert job.status == JobStatus.WAITING
    assert job.assigned_server_id is None


