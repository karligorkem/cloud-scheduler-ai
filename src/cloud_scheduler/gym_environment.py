from functools import partial
from typing import Sequence

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from cloud_scheduler.decision_environment import DecisionEnvironment
from cloud_scheduler.scenario import JobDefinition, create_simulation
from cloud_scheduler.scenario_config import ScenarioConfig


class CloudSchedulerEnv(gym.Env):
    """Cloud Scheduler karar ortamını Gymnasium arayüzüne bağlar."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        max_decisions: int = 1000,
        config: ScenarioConfig | None = None,
        job_definitions: Sequence[JobDefinition] | None = None,
    ) -> None:
        super().__init__()

        if config is None:
            config = ScenarioConfig()

        self.config = config

        self.job_definitions = (
            tuple(job_definitions)
            if job_definitions is not None
            else None
        )

        self.job_count = (
            len(self.job_definitions)
            if self.job_definitions is not None
            else self.config.job_count
        )

        simulation_factory = partial(
            create_simulation,
            config=self.config,
            job_definitions=self.job_definitions,
        )

        self.environment = DecisionEnvironment(
            simulation=simulation_factory(seed=42),
            simulation_factory=simulation_factory,
            max_decisions=max_decisions,
        )

        server_count = len(
            self.environment.simulation.cluster.servers
        )

        self.action_space = spaces.Discrete(server_count + 1)

        observation_size = len(self.environment.observe())

        self.observation_space = spaces.Box(
            low=0.0,
            high=np.inf,
            shape=(observation_size,),
            dtype=np.float32,
        )

        self.has_reset = False

    def reset(self, *, seed=None, options=None):
        """Yeni deney başlatır ve ilk gözlemi döndürür."""

        super().reset(seed=seed)

        episode_seed = int(
            self.np_random.integers(0, 2**31 - 1)
        )

        observation = self.environment.reset(
            seed=episode_seed,
        )

        self.has_reset = True

        info = {
            "episode_seed": episode_seed,
            "action_mask": self.action_masks(),
            "input_mode": (
                "manual"
                if self.job_definitions is not None
                else "synthetic"
            ),
        }

        return (
            np.asarray(observation, dtype=np.float32),
            info,
        )

    def step(self, action):
        """Bir eylem uygular ve Gymnasium sonucunu döndürür."""

        if not self.has_reset:
            raise RuntimeError("Call reset before step.")

        if not self.action_space.contains(action):
            raise ValueError(
                "Action is outside the action space."
            )

        result = self.environment.step(int(action))

        observation = np.asarray(
            result.observation,
            dtype=np.float32,
        )

        info = {
            "action_mask": np.asarray(
                result.action_mask,
                dtype=np.bool_,
            ),
            "current_step": (
                self.environment.simulation.cluster.current_step
            ),
            "completed_count": len(
                self.environment.simulation.completed_jobs
            ),
        }

        return (
            observation,
            result.reward,
            result.terminated,
            result.truncated,
            info,
        )

    def action_masks(self):
        """Geçerli eylemleri maske biçiminde döndürür."""

        return np.asarray(
            self.environment.action_masks(),
            dtype=np.bool_,
        )