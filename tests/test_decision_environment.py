import pytest

from cloud_scheduler.decision_environment import DecisionEnvironment
from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def create_environment(max_decisions: int) -> DecisionEnvironment:
    cluster = Cluster()

    cluster.add_server(
        Server(
            server_id="server-1",
            total_cpu=4,
            total_memory_gb=8.0,
        )
    )

    job = Job(
        job_id="job-1",
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

    return DecisionEnvironment(
        simulation=simulation,
        max_decisions=max_decisions,
    )


def test_environment_returns_completion_after_assignment_and_wait() -> None:
    environment = create_environment(max_decisions=10)

    # İlk sunucuya ata; zaman ilerlemez.
    assigned = environment.step(0)

    assert assigned.reward == 0.0
    assert assigned.terminated is False
    assert assigned.truncated is False
    assert assigned.action_mask == (False, True)
    assert len(assigned.observation) == 10
    assert environment.simulation.cluster.current_step == 0

    # Bekle; bir adımlık görev tamamlanır.
    completed = environment.step(1)

    assert completed.terminated is True
    assert completed.truncated is False
    assert environment.simulation.cluster.current_step == 1

    # Bitmiş deneyde yeni eylem uygulanamaz.
    with pytest.raises(ValueError, match="Episode has ended"):
        environment.step(1)


def test_environment_truncates_when_decision_limit_is_reached() -> None:
    environment = create_environment(max_decisions=1)

    # Görev beklerken zamanı ilerlet.
    result = environment.step(1)

    assert result.reward == -1.0
    assert result.terminated is False
    assert result.truncated is True

    assert environment.decision_count == 1
    assert environment.simulation.queue.peek() is not None

    with pytest.raises(ValueError, match="Episode has ended"):
        environment.step(0)