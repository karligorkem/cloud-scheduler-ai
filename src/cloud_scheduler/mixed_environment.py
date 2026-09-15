from functools import partial

import gymnasium as gym
import numpy as np

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.scenario import create_simulation
from cloud_scheduler.scenario_config import ScenarioConfig


class MixedScenarioEnv(CloudSchedulerEnv):
    """Her yeni deneyde farklı bir senaryo seçer."""

    def __init__(self, max_decisions: int = 1000) -> None:
        self.scenarios = {
            "default": ScenarioConfig(),
            "busy": ScenarioConfig(
                job_count=40,
                max_arrival_step=5,
            ),
            "larger_servers": ScenarioConfig(
                large_server_cpu=16,
                large_server_memory_gb=32.0,
                small_server_cpu=8,
                small_server_memory_gb=16.0,
            ),
        }

        self.scenario_names = tuple(self.scenarios)
        self.current_scenario = "default"

        super().__init__(
            max_decisions=max_decisions,
            config=self.scenarios["default"],
        )

    def reset(self, *, seed=None, options=None):
        """Senaryo seçer ve o ayarlarla temiz bir deney başlatır."""

        # Önce yalnızca Gymnasium'un rastgele sayı kaynağını hazırla.
        gym.Env.reset(self, seed=seed)

        scenario_index = int(
            self.np_random.integers(0, len(self.scenario_names))
        )

        self.current_scenario = self.scenario_names[scenario_index]
        self.config = self.scenarios[self.current_scenario]

        # Yeni deneyin hangi ayarlarla oluşturulacağını belirle.
        self.environment.simulation_factory = partial(
            create_simulation,
            config=self.config,
        )

        episode_seed = int(
            self.np_random.integers(0, 2**31 - 1)
        )

        observation = self.environment.reset(seed=episode_seed)
        self.has_reset = True

        info = {
            "scenario": self.current_scenario,
            "episode_seed": episode_seed,
            "job_count": self.config.job_count,
            "action_mask": self.action_masks(),
        }

        return np.asarray(observation, dtype=np.float32), info

    def step(self, action):
        """Eylemi uygular ve kayıtlara senaryo bilgisini ekler."""

        observation, reward, terminated, truncated, info = (
            super().step(action)
        )

        info["scenario"] = self.current_scenario
        info["job_count"] = self.config.job_count

        return observation, reward, terminated, truncated, info