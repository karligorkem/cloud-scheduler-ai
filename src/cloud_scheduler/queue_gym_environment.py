import numpy as np
from gymnasium import spaces

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.queue_encoder import encode_queue_preview
from cloud_scheduler.scenario_config import ScenarioConfig


class QueueAwareCloudSchedulerEnv(CloudSchedulerEnv):
    """Mevcut gözleme kuyruktaki ilk üç görevin bilgisini ekler."""

    def __init__(
        self,
        max_decisions: int = 1000,
        config: ScenarioConfig | None = None,
    ) -> None:
        super().__init__(
            max_decisions=max_decisions,
            config=config,
        )

        original_size = self.observation_space.shape[0]
        queue_preview_size = 3 * 4

        self.observation_space = spaces.Box(
            low=0.0,
            high=np.inf,
            shape=(original_size + queue_preview_size,),
            dtype=np.float32,
        )

    def _extend_observation(
        self,
        observation: np.ndarray,
    ) -> np.ndarray:
        """Temel gözlemle kuyruk bilgilerini birleştirir."""

        queue = self.environment.simulation.queue

        queue_values = np.asarray(
            encode_queue_preview(queue),
            dtype=np.float32,
        )

        return np.concatenate((observation, queue_values))

    def reset(self, *, seed=None, options=None):
        """Yeni deney başlatır ve genişletilmiş gözlemi döndürür."""

        observation, info = super().reset(
            seed=seed,
            options=options,
        )

        return self._extend_observation(observation), info

    def step(self, action):
        """Eylemi uygular ve güncel kuyruk bilgilerini gözleme ekler."""

        observation, reward, terminated, truncated, info = super().step(
            action
        )

        return (
            self._extend_observation(observation),
            reward,
            terminated,
            truncated,
            info,
        )