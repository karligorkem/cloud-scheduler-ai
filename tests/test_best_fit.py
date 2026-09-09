from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.best_fit import BestFitScheduler


def test_best_fit_chooses_tighter_server_and_starts_job() -> None:
    cluster = Cluster()

    large_server = Server(
        server_id="large-server",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    small_server = Server(
        server_id="small-server",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    # Büyük sunucuyu önce ekliyoruz.
    # First Fit bu sırada büyük sunucuyu seçerdi.
    cluster.add_server(large_server)
    cluster.add_server(small_server)

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
    )

    queue = JobQueue()
    queue.add(job)

    scheduler = BestFitScheduler()

    started = scheduler.schedule_next(cluster, queue)

    assert started is True

    # Listede ikinci olmasına rağmen küçük sunucu seçilmeli.
    assert job.assigned_server_id == "small-server"
    assert job.status == JobStatus.RUNNING
    assert job.started_step == 0
    assert queue.peek() is None

    # Küçük sunucunun kaynakları kullanılmalı.
    assert small_server.available_cpu == 2
    assert small_server.available_memory_gb == 4.0

    # Büyük sunucu boş kalmalı.
    assert large_server.available_cpu == 8
    assert large_server.available_memory_gb == 16.0


def test_best_fit_skips_server_with_insufficient_memory() -> None:
    cluster = Cluster()

    insufficient_server = Server(
        server_id="insufficient-server",
        total_cpu=2,
        total_memory_gb=2.0,
    )

    suitable_server = Server(
        server_id="suitable-server",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    cluster.add_server(insufficient_server)
    cluster.add_server(suitable_server)

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    scheduler = BestFitScheduler()

    selected_server = scheduler.select_server(cluster, job)

    # İlk sunucu CPU açısından tam uysa da RAM'i yetersiz.
    assert selected_server is suitable_server

    # Sadece seçim yapmak görevi başlatmamalı.
    assert job.status == JobStatus.WAITING
    assert job.assigned_server_id is None
    assert suitable_server.available_cpu == 8
    assert suitable_server.available_memory_gb == 16.0