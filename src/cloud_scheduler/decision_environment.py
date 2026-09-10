from collections.abc import Callable
from dataclasses import dataclass

from cloud_scheduler.action_executor import ActionExecutor
from cloud_scheduler.action_mask import build_action_mask
from cloud_scheduler.observation import build_observation
from cloud_scheduler.observation_encoder import ObservationEncoder
from cloud_scheduler.reward import calculate_reward
from cloud_scheduler.simulation import Simulation


@dataclass(frozen=True)
class DecisionResult:
    """Bir eylemin sonucunu tutar."""

    observation: tuple[float, ...]
    action_mask: tuple[bool, ...]
    reward: float
    terminated: bool
    truncated: bool


class DecisionEnvironment:
    """Eylemleri uygular ve yeni deneyler baslatir."""

    def __init__(
        self,
        simulation: Simulation,
        max_decisions: int = 1000,
        simulation_factory: Callable[[int], Simulation] | None = None,
    ) -> None:
        if max_decisions <= 0:
            raise ValueError("Max decisions must be greater than zero.")

        self.simulation = simulation
        self.executor = ActionExecutor(simulation)

        self.encoder = ObservationEncoder(
            server_count=len(simulation.cluster.servers),
        )

        # Yeni deney olusturacak fonksiyonu sakla.
        self.simulation_factory = simulation_factory

        self.max_decisions = max_decisions
        self.decision_count = 0
        self.closed = simulation.is_finished()

    def reset(self, seed: int = 42) -> tuple[float, ...]:
        """Yeni bir deney baslatir ve ilk gozlemi dondurur."""

        if self.simulation_factory is None:
            raise ValueError("Reset requires a simulation factory.")

        new_simulation = self.simulation_factory(seed)

        if len(new_simulation.cluster.servers) != self.encoder.server_count:
            raise ValueError("Reset must preserve the server count.")

        self.simulation = new_simulation
        self.executor = ActionExecutor(new_simulation)

        self.decision_count = 0
        self.closed = new_simulation.is_finished()

        return self.observe()

    def observe(self) -> tuple[float, ...]:
        """Mevcut durumu sayisal gozleme donusturur."""

        observation = build_observation(
            self.simulation.cluster,
            self.simulation.queue,
        )

        return tuple(self.encoder.encode(observation))

    def action_masks(self) -> tuple[bool, ...]:
        """Gecerli eylemleri gosterir."""

        return build_action_mask(
            self.simulation.cluster,
            self.simulation.queue,
        )

    def step(self, action: int) -> DecisionResult:
        """Bir eylem uygular ve sonucunu dondurur."""

        if self.closed:
            raise ValueError("Episode has ended.")

        previous_observation = build_observation(
            self.simulation.cluster,
            self.simulation.queue,
        )

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