import pytest

from cloud_scheduler.scenario import create_simulation
from cloud_scheduler.scenario_config import ScenarioConfig


def test_scenario_applies_custom_settings() -> None:
    config = ScenarioConfig(
        job_count=7,
        max_arrival_step=3,
        large_server_cpu=16,
        large_server_memory_gb=32.0,
        small_server_cpu=8,
        small_server_memory_gb=16.0,
    )

    simulation = create_simulation(seed=42, config=config)

    large_server, small_server = simulation.cluster.servers

    assert large_server.total_cpu == 16
    assert large_server.total_memory_gb == 32.0

    assert small_server.total_cpu == 8
    assert small_server.total_memory_gb == 16.0

    assert len(simulation.pending_jobs) == 7

    for job in simulation.pending_jobs:
        assert 0 <= job.arrival_step <= 3

    # Varsayılan senaryo özel ayarlardan etkilenmemeli.
    default_simulation = create_simulation(seed=42)

    assert len(default_simulation.pending_jobs) == 20
    assert default_simulation.cluster.servers[0].total_cpu == 8


def test_scenario_config_rejects_zero_job_count() -> None:
    with pytest.raises(
        ValueError,
        match="Job count must be greater than zero",
    ):
        ScenarioConfig(job_count=0)