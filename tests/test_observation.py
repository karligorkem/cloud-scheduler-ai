from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.observation import build_observation


def test_observation_captures_state_without_changing_it() -> None:
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
    )

    queue = JobQueue()
    queue.add(job)

    # Görev kuyrukta beklerken iki zaman adımı geçsin.
    cluster.advance_time()
    cluster.advance_time()

    observation = build_observation(cluster, queue)

    assert observation.current_step == 2
    assert observation.queue_length == 1
    assert len(observation.servers) == 1

    assert observation.servers[0].available_cpu == 4
    assert observation.servers[0].available_memory_gb == 8.0

    assert observation.next_job is not None
    assert observation.next_job.job_id == "job-1"
    assert observation.next_job.required_cpu == 2
    assert observation.next_job.waiting_steps == 2

    # Gözlem almak sistemi değiştirmemeli.
    assert cluster.current_step == 2
    assert queue.peek() is job
    assert job.status == JobStatus.WAITING
    assert server.available_cpu == 4

    # Sistem sonradan değişse bile eski gözlem aynı kalmalı.
    server.allocate(job)

    assert server.available_cpu == 2
    assert observation.servers[0].available_cpu == 4


def test_observation_handles_empty_queue_and_cluster() -> None:
    cluster = Cluster()
    queue = JobQueue()

    observation = build_observation(cluster, queue)

    assert observation.current_step == 0
    assert observation.queue_length == 0
    assert observation.servers == ()
    assert observation.next_job is None