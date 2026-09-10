from cloud_scheduler.action_mask import build_action_mask
from cloud_scheduler.domain.job import Job
from cloud_scheduler.simulation import Simulation


class ActionExecutor:
    """Dışarıdan seçilen atama veya bekleme eylemini uygular."""

    def __init__(self, simulation: Simulation) -> None:
        self.simulation = simulation

        # İlk karar öncesinde zamanı gelmiş görevleri kuyruğa al.
        self.simulation.admit_arrivals()

    def apply(self, action: int) -> list[Job]:
        """Eylemi uygular ve bu işlemde tamamlanan görevleri döndürür."""

        if self.simulation.is_finished():
            raise ValueError("Simulation has already finished.")

        # Negatif indekslerin Python'da son elemanı seçmesini engelle.
        if type(action) is not int:
            raise ValueError("Action must be an integer.")

        wait_action = len(self.simulation.cluster.servers)

        if action < 0 or action > wait_action:
            raise ValueError("Action index is out of range.")

        mask = build_action_mask(
            self.simulation.cluster,
            self.simulation.queue,
        )

        if not mask[action]:
            raise ValueError("Action is not valid in the current state.")

        if action == wait_action:
            completed_jobs = self.simulation.advance_one_step()

            # Yeni zamana ulaştık; sonraki karar için gelişleri kabul et.
            self.simulation.admit_arrivals()

            return completed_jobs

        job = self.simulation.queue.peek()

        if job is None:
            raise ValueError("No waiting job is available.")

        server = self.simulation.cluster.servers[action]

        server.allocate(job)
        job.started_step = self.simulation.cluster.current_step
        self.simulation.queue.pop_next()

        # Atama zamanı ilerletmediğinden tamamlanan görev yok.
        return []