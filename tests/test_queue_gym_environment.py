import numpy as np

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.queue_encoder import encode_queue_preview
from cloud_scheduler.queue_gym_environment import QueueAwareCloudSchedulerEnv


def test_queue_environment_extends_observation_without_changing_dynamics() -> None:
    original = CloudSchedulerEnv()
    extended = QueueAwareCloudSchedulerEnv()

    try:
        original_observation, original_info = original.reset(seed=42)
        extended_observation, extended_info = extended.reset(seed=42)

        # Aynı seed aynı görevleri üretmeli.
        assert original_info["episode_seed"] == extended_info["episode_seed"]

        assert extended_observation.shape == (26,)
        assert extended_observation.dtype == np.float32
        assert extended.observation_space.contains(extended_observation)

        # İlk 14 sayı mevcut ortamla aynı olmalı.
        np.testing.assert_array_equal(
            extended_observation[:14],
            original_observation,
        )

        # Deney boyunca iki ortama da aynı eylemi uygula.
        for _ in range(1000):
            original_mask = original.action_masks()
            extended_mask = extended.action_masks()

            np.testing.assert_array_equal(original_mask, extended_mask)

            # İlk geçerli eylemi seç: uygun sunucu varsa ata, yoksa bekle.
            action = int(np.flatnonzero(original_mask)[0])

            original_result = original.step(action)
            extended_result = extended.step(action)

            original_observation, reward, terminated, truncated, _ = original_result
            extended_observation, new_reward, new_terminated, new_truncated, _ = (
                extended_result
            )

            # Ek bilgi, ödülü veya simülasyonun ilerleyişini değiştirmemeli.
            assert new_reward == reward
            assert new_terminated == terminated
            assert new_truncated == truncated

            np.testing.assert_array_equal(
                extended_observation[:14],
                original_observation,
            )

            # Son 12 sayı güncel kuyruğu temsil etmeli.
            expected_queue = np.asarray(
                encode_queue_preview(extended.environment.simulation.queue),
                dtype=np.float32,
            )

            np.testing.assert_array_equal(
                extended_observation[14:],
                expected_queue,
            )

            assert extended.observation_space.contains(extended_observation)

            if terminated or truncated:
                assert terminated
                assert not truncated
                break
        else:
            raise AssertionError("Episode did not end within the test limit.")

    finally:
        original.close()
        extended.close()