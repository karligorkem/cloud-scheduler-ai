from typing import Protocol

from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job_queue import JobQueue


class Scheduler(Protocol):
    """Simülasyonun kullanabileceği zamanlayıcının ortak arayüzü."""

    def schedule_next(
        self,
        cluster: Cluster,
        queue: JobQueue,
    ) -> bool:
        """Bir görev başlatırsa True, başlatamazsa False döndürür."""
        ...