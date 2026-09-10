import pytest

from cloud_scheduler.action_executor import ActionExecutor
from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job, JobStatus
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def test_wait_does_not_automatically_allocate_job() -> None:
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
        duration_steps=1,
        arrival_step=1,
    )

    simulation = Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=[job],
    )

    executor = ActionExecutor(simulation)

    # Tek sunucu var: 0 atama, 1 bekleme.
    executor.apply(1)

    assert cluster.current_step == 1
    assert simulation.queue.peek() is job
    assert job.status == JobStatus.WAITING
    assert job.started_step is None

    # Sunucuyu seç: görev başlasın ama zaman ilerlemesin.
    completed_jobs = executor.apply(0)

    assert completed_jobs == []
    assert cluster.current_step == 1
    assert job.started_step == 1
    assert job.status == JobStatus.RUNNING

    # Bir adım çalıştırınca görev tamamlanmalı.
    completed_jobs = executor.apply(1)

    assert completed_jobs == [job]
    assert job.completed_step == 2
    assert simulation.is_finished() is True

    # Boş geçen ve çalışılan aralıklar ayrı kaydedilmeli.
    assert len(simulation.resource_history) == 2
    assert simulation.resource_history[0].cpu_utilization == 0.0
    assert simulation.resource_history[1].cpu_utilization == 0.5


def test_invalid_assignment_does_not_change_state() -> None:
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=1,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    job = Job(
        job_id="large-job",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    simulation = Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=[job],
    )

    executor = ActionExecutor(simulation)

    with pytest.raises(ValueError, match="Action is not valid"):
        executor.apply(0)

    assert cluster.current_step == 0
    assert server.available_cpu == 1
    assert server.available_memory_gb == 8.0
    assert simulation.queue.peek() is job
    assert job.status == JobStatus.WAITING
    assert job.started_step is None
    assert simulation.resource_history == []