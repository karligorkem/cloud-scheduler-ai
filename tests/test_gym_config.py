from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.scenario_config import ScenarioConfig


def test_gym_reset_preserves_custom_scenario_settings() -> None:
    config = ScenarioConfig(
        job_count=7,
        max_arrival_step=3,
        large_server_cpu=16,
        large_server_memory_gb=32.0,
        small_server_cpu=8,
        small_server_memory_gb=16.0,
    )

    env = CloudSchedulerEnv(config=config)

    try:
        for seed in [10, 20]:
            observation, info = env.reset(seed=seed)

            simulation = env.environment.simulation
            large_server, small_server = simulation.cluster.servers

            assert large_server.total_cpu == 16
            assert large_server.total_memory_gb == 32.0

            assert small_server.total_cpu == 8
            assert small_server.total_memory_gb == 16.0

            # Sıfırıncı adımda gelenler kuyruğa alınmış olabilir.
            all_jobs = (
                simulation.pending_jobs + simulation.queue.jobs
            )

            assert len(all_jobs) == 7

            for job in all_jobs:
                assert 0 <= job.arrival_step <= 3

            assert simulation.cluster.current_step == 0
            assert simulation.completed_jobs == []
            assert simulation.resource_history == []

            assert observation.shape == (14,)
            assert env.observation_space.contains(observation)
            assert env.action_space.n == 3
            assert len(info["action_mask"]) == 3

            # Durumu değiştir; sonraki reset temiz başlangıç yapmalı.
            env.step(2)

            assert simulation.cluster.current_step == 1

    finally:
        env.close()