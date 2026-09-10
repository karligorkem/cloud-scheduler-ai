from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation
import pytest

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
        # İlk görev hemen başlar ve iki adım sonra biter.
    assert first_job.arrival_step == 0
    assert first_job.started_step == 0
    assert first_job.completed_step == 2
    assert first_job.waiting_steps == 0
    assert first_job.turnaround_steps == 2

    # İkinci görev kaynakların boşalmasını iki adım bekler.
    assert second_job.arrival_step == 0
    assert second_job.started_step == 2
    assert second_job.completed_step == 3
    assert second_job.waiting_steps == 2
    assert second_job.turnaround_steps == 3


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
        # Hiç başlayamayan görevin başlama ve bitiş zamanı olmamalı.
    assert job.started_step is None
    assert job.completed_step is None

    # Kesinleşmiş bekleme ve toplam süre henüz hesaplanamaz.
    assert job.waiting_steps is None
    assert job.turnaround_steps is None

def test_simulation_waits_until_job_arrives() -> None:
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    job = Job(
        job_id="late-job",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=2,
        arrival_step=3,
    )

    simulation = Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=[job],
    )

    # Gelecekte gelecek görev varsa simülasyon bitmiş sayılmaz.
    assert simulation.is_finished() is False

    # Zamanı 0'dan 3'e getir.
    for _ in range(3):
        simulation.step()

    # Görev henüz başlamamış ve kaynak tüketmemiş olmalı.
    assert cluster.current_step == 3
    assert job.started_step is None
    assert server.running_jobs == []
    assert server.available_cpu == 4
    assert server.available_memory_gb == 8.0

    # 3. adımın başında kabul edilir, ardından bir adım çalışır.
    simulation.step()

    assert job.started_step == 3
    assert job.status == JobStatus.RUNNING
    assert job.remaining_steps == 1
    assert job.waiting_steps == 0

    # İkinci çalışma adımında tamamlanır.
    completed_jobs = simulation.step()

    assert completed_jobs == [job]
    assert job.completed_step == 5
    assert job.turnaround_steps == 2
    assert simulation.is_finished() is True

def test_simulation_records_resources_before_job_finishes() -> None:
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=2.0,
        duration_steps=1,
        arrival_step=1,
    )

    simulation = Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=[job],
    )

    simulation.run(max_steps=10)

    assert simulation.is_finished() is True
    assert len(simulation.resource_history) == 2

    # 0 → 1 aralığında görev henüz gelmemiştir.
    idle_snapshot = simulation.resource_history[0]

    assert idle_snapshot.step == 0
    assert idle_snapshot.cpu_utilization == 0.0
    assert idle_snapshot.memory_utilization == 0.0

    # 1 → 2 aralığında görev çalışır.
    busy_snapshot = simulation.resource_history[1]

    assert busy_snapshot.step == 1
    assert busy_snapshot.cpu_utilization == 0.5
    assert busy_snapshot.memory_utilization == 0.25

    # Görev bitince kaynaklar boşalır ama geçmiş ölçüm korunur.
    assert server.available_cpu == 4
    assert server.available_memory_gb == 8.0
    assert busy_snapshot.cpu_utilization == 0.5

def test_resource_history_matches_total_job_work() -> None:
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
        arrival_step=2,
    )

    simulation = Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=[job],
    )

    simulation.run(max_steps=10)

    assert simulation.is_finished() is True

    # İki adım boş geçer, görev üç adım çalışır.
    assert cluster.current_step == 5
    assert len(simulation.resource_history) == 5

    measured_cpu_steps = 0.0
    measured_memory_steps = 0.0

    for snapshot in simulation.resource_history:
        measured_cpu_steps = measured_cpu_steps + (
            snapshot.cpu_utilization * server.total_cpu
        )

        measured_memory_steps = measured_memory_steps + (
            snapshot.memory_utilization * server.total_memory_gb
        )

    expected_cpu_steps = job.required_cpu * job.duration_steps

    expected_memory_steps = (
        job.required_memory_gb * job.duration_steps
    )

    assert measured_cpu_steps == pytest.approx(expected_cpu_steps)
    assert measured_memory_steps == pytest.approx(expected_memory_steps)