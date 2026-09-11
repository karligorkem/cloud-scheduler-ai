import gymnasium as gym
import numpy as np
from gymnasium import spaces

from cloud_scheduler.decision_environment import DecisionEnvironment
from cloud_scheduler.scenario import create_simulation


class CloudSchedulerEnv(gym.Env):
    """Karar ortamını Gymnasium arayüzüne bağlar."""

    metadata = {"render_modes": []}

    def __init__(self, max_decisions: int = 1000) -> None:
        super().__init__()

        self.environment = DecisionEnvironment(
            simulation=create_simulation(seed=42),
            simulation_factory=create_simulation,
            max_decisions=max_decisions,
        )

        server_count = len(
            self.environment.simulation.cluster.servers
        )

        # Her sunucu için bir atama ve en sonda bekleme.
        self.action_space = spaces.Discrete(server_count + 1)

        observation_size = len(self.environment.observe())

        # Ölçeklenmiş değerler 1'i aşabilir; üst sınırı 1 yapmıyoruz.
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

        # Gymnasium'un rastgele sayı kaynağından deney seed'i üret.
        episode_seed = int(
            self.np_random.integers(0, 2**31 - 1)
        )

        observation = self.environment.reset(seed=episode_seed)
        self.has_reset = True

        info = {
            "episode_seed": episode_seed,
            "action_mask": self.action_masks(),
        }

        return np.asarray(observation, dtype=np.float32), info

    def step(self, action):
        """Bir eylem uygular ve Gymnasium biçiminde sonuç döndürür."""

        if not self.has_reset:
            raise RuntimeError("Call reset before step.")

        if not self.action_space.contains(action):
            raise ValueError("Action is outside the action space.")

        # NumPy tam sayısını mevcut executor'ın istediği Python int'e çevir.
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
        """Maske destekleyen politika için geçerli eylemleri verir."""

        return np.asarray(
            self.environment.action_masks(),
            dtype=np.bool_,
        )