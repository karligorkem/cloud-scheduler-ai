from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.server import Server


def test_advance_time_decreases_remaining_duration() -> None:
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

    completed_jobs = server.advance_time()

    # Bir adım geçti ancak görev henüz tamamlanmadı.
    assert job.remaining_steps == 2
    assert job.status == JobStatus.RUNNING
    assert completed_jobs == []

    # Görev çalıştığı için kaynaklar hâlâ ayrılmış durumda.
    assert server.available_cpu == 6
    assert server.available_memory_gb == 12.0
    assert job in server.running_jobs


def test_completed_job_releases_resources_only_once() -> None:
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
        duration_steps=1,
        required_gpu_count=1,
    )

    server.allocate(job)

    completed_jobs = server.advance_time()

    # Tek adımlık görev tamamlandı.
    assert job.remaining_steps == 0
    assert job.status == JobStatus.COMPLETED
    assert completed_jobs == [job]
    assert server.running_jobs == []

    # Kaynakların tamamı geri geldi.
    assert server.available_cpu == 8
    assert server.available_memory_gb == 16.0
    assert server.available_gpu_count == 2

    # Görevin çalıştığı sunucu bilgisi korunuyor.
    assert job.assigned_server_id == "server-1"

    # Tekrar ilerletmek biten görevi yeniden işlememeli.
    completed_again = server.advance_time()

    assert completed_again == []
    assert job.remaining_steps == 0
    assert server.available_cpu == 8
    assert server.available_memory_gb == 16.0
    assert server.available_gpu_count == 2