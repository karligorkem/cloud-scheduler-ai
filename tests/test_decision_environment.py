import pytest

from cloud_scheduler.decision_environment import DecisionEnvironment
from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.scenario import create_simulation
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def create_environment(max_decisions: int) -> DecisionEnvironment:
    """Testler için tek sunuculu, tek görevli ortam oluşturur."""

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

    # Görevi sunucuya ata. Zaman henüz ilerlemez.
    assigned = environment.step(0)

    assert assigned.reward == 0.0
    assert assigned.terminated is False
    assert assigned.truncated is False
    assert assigned.action_mask == (False, True)
    assert len(assigned.observation) == 10
    assert environment.simulation.cluster.current_step == 0

    # Bir adım bekle. Görev tamamlanır.
    completed = environment.step(1)

    assert completed.terminated is True
    assert completed.truncated is False
    assert environment.simulation.cluster.current_step == 1

    with pytest.raises(ValueError, match="Episode has ended"):
        environment.step(1)


def test_environment_truncates_when_decision_limit_is_reached() -> None:
    environment = create_environment(max_decisions=1)

    # Görev kuyrukta beklerken bir adım geçir.
    result = environment.step(1)

    assert result.reward == -1.0
    assert result.terminated is False
    assert result.truncated is True
    assert environment.decision_count == 1
    assert environment.simulation.queue.peek() is not None

    with pytest.raises(ValueError, match="Episode has ended"):
        environment.step(0)


def test_reset_restores_initial_state_with_same_seed() -> None:
    environment = DecisionEnvironment(
        simulation=create_simulation(seed=42),
        simulation_factory=create_simulation,
        max_decisions=1,
    )

    initial_observation = environment.observe()
    initial_mask = environment.action_masks()

    old_simulation = environment.simulation
    old_server = old_simulation.cluster.servers[0]

    wait_action = len(old_simulation.cluster.servers)

    # Bir karar vererek karar sınırına ulaş.
    result = environment.step(wait_action)

    assert result.truncated is True
    assert environment.closed is True
    assert environment.decision_count == 1
    assert old_simulation.cluster.current_step == 1
    assert len(old_simulation.resource_history) == 1

    # Aynı seed ile yeni bir deney başlat.
    reset_observation = environment.reset(seed=42)

    assert reset_observation == initial_observation
    assert environment.action_masks() == initial_mask
    assert environment.closed is False
    assert environment.decision_count == 0

    assert environment.simulation.cluster.current_step == 0
    assert environment.simulation.completed_jobs == []
    assert environment.simulation.resource_history == []

    # Eski nesneler tekrar kullanılmamalı.
    assert environment.simulation is not old_simulation
    assert environment.simulation.cluster.servers[0] is not old_server

    # Yeni deney tekrar eylem kabul etmeli.
    environment.step(wait_action)

    assert environment.decision_count == 1