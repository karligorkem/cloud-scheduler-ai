from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def test_simulation_completes_jobs_and_restores_resources() -> None:
    # Tek sunuculu bir küme oluştur.
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
        gpu_count=1,
    )

    cluster.add_server(server)

    # İlk görev sunucunun bütün kaynaklarını kullanacak.
    first_job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=2,
        required_gpu_count=1,
    )

    # İkinci görev, ilk görev tamamlanana kadar bekleyecek.
    second_job = Job(
        job_id="job-2",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    queue = JobQueue()
    queue.add(first_job)
    queue.add(second_job)

    scheduler = FirstFitScheduler()

    simulation = Simulation(
        cluster=cluster,
        queue=queue,
        scheduler=scheduler,
    )

    completed_jobs = simulation.run(max_steps=10)

    # İlk görev 2, ikinci görev 1 adım sürer.
    assert cluster.current_step == 3

    # Görevler tamamlanma sırasıyla dönmeli.
    assert completed_jobs == [first_job, second_job]

    assert first_job.status == JobStatus.COMPLETED
    assert second_job.status == JobStatus.COMPLETED

    # Bekleyen veya çalışan görev kalmamalı.
    assert queue.peek() is None
    assert server.running_jobs == []
    assert simulation.is_finished() is True

    # Bütün kaynaklar tekrar kullanılabilir olmalı.
    assert server.available_cpu == 4
    assert server.available_memory_gb == 8.0
    assert server.available_gpu_count == 1


def test_simulation_stops_at_limit_when_job_cannot_fit() -> None:
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    # Sunucuda 4 CPU var, görev ise 8 CPU istiyor.
    job = Job(
        job_id="large-job",
        required_cpu=8,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    queue = JobQueue()
    queue.add(job)

    scheduler = FirstFitScheduler()

    simulation = Simulation(
        cluster=cluster,
        queue=queue,
        scheduler=scheduler,
    )

    completed_jobs = simulation.run(max_steps=5)

    # Görev başlayamasa bile belirlenen sınırda durmalı.
    assert cluster.current_step == 5

    # Tamamlanan görev olmamalı.
    assert completed_jobs == []

    # Simülasyon durdu ama iş henüz bitmedi.
    assert simulation.is_finished() is False
    assert queue.peek() is job
    assert job.status == JobStatus.WAITING
    assert job.assigned_server_id is None

    # Başlatılamayan görev kaynak tüketmemeli.
    assert server.running_jobs == []
    assert server.available_cpu == 4
    assert server.available_memory_gb == 8.0