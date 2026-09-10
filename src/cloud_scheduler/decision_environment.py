from dataclasses import dataclass

from cloud_scheduler.action_executor import ActionExecutor
from cloud_scheduler.action_mask import build_action_mask
from cloud_scheduler.observation import build_observation
from cloud_scheduler.observation_encoder import ObservationEncoder
from cloud_scheduler.reward import calculate_reward
from cloud_scheduler.simulation import Simulation


@dataclass(frozen=True)
class DecisionResult:
    """Bir kararın ardından eğitim döngüsüne verilen sonuç."""

    observation: tuple[float, ...]
    action_mask: tuple[bool, ...]
    reward: float
    terminated: bool
    truncated: bool


class DecisionEnvironment:
    """Seçilen eylemi uygular ve yeni durumla ödülü birlikte döndürür."""

    def __init__(
        self,
        simulation: Simulation,
        max_decisions: int = 1000,
    ) -> None:
        if max_decisions <= 0:
            raise ValueError("Max decisions must be greater than zero.")

        self.simulation = simulation
        self.executor = ActionExecutor(simulation)

        self.encoder = ObservationEncoder(
            server_count=len(simulation.cluster.servers),
        )

        self.max_decisions = max_decisions
        self.decision_count = 0
        self.closed = simulation.is_finished()

    def observe(self) -> tuple[float, ...]:
        """Mevcut gözlemi sayı dizisine dönüştürür."""

        observation = build_observation(
            self.simulation.cluster,
            self.simulation.queue,
        )

        return tuple(self.encoder.encode(observation))

    def action_masks(self) -> tuple[bool, ...]:
        """Mevcut durumda geçerli eylemleri verir."""

        return build_action_mask(
            self.simulation.cluster,
            self.simulation.queue,
        )

    def step(self, action: int) -> DecisionResult:
        """Bir karar uygular; bu her zaman zamanı ilerletmez."""

        if self.closed:
            raise ValueError("Episode has ended.")

        previous_observation = build_observation(
            self.simulation.cluster,
            self.simulation.queue,
        )

        # Geçersiz eylem hata verirse aşağıdaki sayaç güncellenmez.
        self.executor.apply(action)

        reward = calculate_reward(previous_observation, action)

        self.decision_count = self.decision_count + 1

        terminated = self.simulation.is_finished()

        truncated = (
            not terminated
            and self.decision_count >= self.max_decisions
        )

        self.closed = terminated or truncated

        return DecisionResult(
            observation=self.observe(),
            action_mask=self.action_masks(),
            reward=reward,
            terminated=terminated,
            truncated=truncated,
        )