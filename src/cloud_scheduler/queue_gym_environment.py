from typing import Sequence

import numpy as np
from gymnasium import spaces

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.queue_encoder import encode_queue_preview
from cloud_scheduler.scenario import JobDefinition
from cloud_scheduler.scenario_config import ScenarioConfig


class QueueAwareCloudSchedulerEnv(CloudSchedulerEnv):
    """Kuyruktaki ilk görevleri de gözleme ekleyen ortam."""

    def __init__(
        self,
        max_decisions: int = 1000,
        config: ScenarioConfig | None = None,
        job_definitions: Sequence[JobDefinition] | None = None,
    ) -> None:
        super().__init__(
            max_decisions=max_decisions,
            config=config,
            job_definitions=job_definitions,
        )

        base_size = self.observation_space.shape[0]
        preview_size = len(
            encode_queue_preview(
                self.environment.simulation.queue
            )
        )

        self.observation_space = spaces.Box(
            low=0.0,
            high=np.inf,
            shape=(base_size + preview_size,),
            dtype=np.float32,
        )

    def extend_observation(
        self,
        observation: np.ndarray,
    ) -> np.ndarray:
        queue_preview = np.asarray(
            encode_queue_preview(
                self.environment.simulation.queue
            ),
            dtype=np.float32,
        )

        return np.concatenate(
            [observation, queue_preview]
        ).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        observation, info = super().reset(
            seed=seed,
            options=options,
        )

        return self.extend_observation(observation), info

    def step(self, action):
        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = super().step(action)

        return (
            self.extend_observation(observation),
            reward,
            terminated,
            truncated,
            info,
        )