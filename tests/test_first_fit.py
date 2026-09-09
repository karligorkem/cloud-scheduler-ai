from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler


def test_scheduler_uses_first_suitable_server() -> None:
    cluster = Cluster()
    queue = JobQueue()
    scheduler = FirstFitScheduler()

    small_server = Server(
        server_id="small-server",
        total_cpu=2,
        total_memory_gb=16.0,
    )

    suitable_server = Server(
        server_id="suitable-server",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    larger_server = Server(
        server_id="larger-server",
        total_cpu=16,
        total_memory_gb=32.0,
    )

    cluster.add_server(small_server)
    cluster.add_server(suitable_server)
    cluster.add_server(larger_server)

    job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=3,
    )

    queue.add(job)

    result = scheduler.schedule_next(cluster, queue)

    assert result is True
    assert job.assigned_server_id == "suitable-server"
    assert job.status == JobStatus.RUNNING
    assert queue.peek() is None

    # Yalnızca seçilen sunucunun kaynakları azalmalı.
    assert small_server.available_cpu == 2
    assert suitable_server.available_cpu == 4
    assert larger_server.available_cpu == 16

def test_scheduler_waits_until_resources_become_available() -> None:
    cluster = Cluster()
    queue = JobQueue()
    scheduler = FirstFitScheduler()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    running_job = Job(
        job_id="running-job",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=1,
    )

    waiting_job = Job(
        job_id="waiting-job",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
    )

    server.allocate(running_job)
    queue.add(waiting_job)

    # Sunucu doluyken yeni görev başlatılamaz.
    first_result = scheduler.schedule_next(cluster, queue)

    assert first_result is False
    assert queue.peek() is waiting_job
    assert waiting_job.status == JobStatus.WAITING
    assert waiting_job.assigned_server_id is None

    # Bir adım sonra çalışan görev biter ve kaynaklar boşalır.
    cluster.advance_time()

    second_result = scheduler.schedule_next(cluster, queue)

    assert second_result is True
    assert running_job.status == JobStatus.COMPLETED
    assert waiting_job.status == JobStatus.RUNNING
    assert waiting_job.assigned_server_id == "server-1"
    assert queue.peek() is None

    # Atama yapmak zamanı ilerletmez.
    assert waiting_job.remaining_steps == 3

def test_scheduler_returns_false_for_empty_queue() -> None:
    cluster = Cluster()
    queue = JobQueue()
    scheduler = FirstFitScheduler()

    result = scheduler.schedule_next(cluster, queue)

    assert result is False
    assert queue.jobs == []