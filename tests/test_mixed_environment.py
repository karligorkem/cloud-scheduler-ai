import numpy as np

from cloud_scheduler.mixed_environment import MixedScenarioEnv


def test_mixed_resets_are_reproducible_and_apply_selected_settings() -> None:
    first_env = MixedScenarioEnv()
    second_env = MixedScenarioEnv()

    try:
        for episode in range(10):
            # Yalnızca ilk reset'te seed ver.
            seed = 42 if episode == 0 else None

            first_observation, first_info = first_env.reset(seed=seed)
            second_observation, second_info = second_env.reset(seed=seed)

            # Aynı başlangıç seed'i aynı senaryo ve görev sırasını üretmeli.
            assert first_info["scenario"] == second_info["scenario"]
            assert first_info["episode_seed"] == second_info["episode_seed"]

            np.testing.assert_array_equal(
                first_observation,
                second_observation,
            )

            simulation = first_env.environment.simulation
            config = first_env.config

            all_jobs = (
                simulation.pending_jobs + simulation.queue.jobs
            )

            assert len(all_jobs) == config.job_count

            large_server, small_server = simulation.cluster.servers

            assert large_server.total_cpu == config.large_server_cpu
            assert (
                large_server.total_memory_gb
                == config.large_server_memory_gb
            )

            assert small_server.total_cpu == config.small_server_cpu
            assert (
                small_server.total_memory_gb
                == config.small_server_memory_gb
            )

            assert simulation.cluster.current_step == 0
            assert simulation.completed_jobs == []
            assert simulation.resource_history == []

            assert first_observation.shape == (14,)
            assert first_env.observation_space.contains(first_observation)
            assert first_env.action_space.n == 3

            # Durumu değiştir; sonraki reset bu kayıtları temizlemeli.
            first_env.step(2)
            second_env.step(2)

            assert simulation.cluster.current_step == 1

    finally:
        first_env.close()
        second_env.close()