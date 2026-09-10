from dataclasses import dataclass

from cloud_scheduler.domain.cluster import Cluster


@dataclass(frozen=True)
class ResourceSnapshot:
    """Bir zaman aralığı boyunca ayrılmış kaynakların ölçümü."""

    step: int
    cpu_utilization: float
    memory_utilization: float


def measure_resources(cluster: Cluster) -> ResourceSnapshot:
    """Kümenin toplam kapasitesine göre kaynak kullanımını hesaplar."""

    total_cpu = 0
    used_cpu = 0

    total_memory_gb = 0.0
    used_memory_gb = 0.0

    for server in cluster.servers:
        total_cpu = total_cpu + server.total_cpu
        used_cpu = used_cpu + (
            server.total_cpu - server.available_cpu
        )

        total_memory_gb = total_memory_gb + server.total_memory_gb
        used_memory_gb = used_memory_gb + (
            server.total_memory_gb - server.available_memory_gb
        )

    # Boş bir kümede sıfıra bölme yapma.
    cpu_utilization = 0.0
    memory_utilization = 0.0

    if total_cpu > 0:
        cpu_utilization = used_cpu / total_cpu

    if total_memory_gb > 0:
        memory_utilization = used_memory_gb / total_memory_gb

    return ResourceSnapshot(
        step=cluster.current_step,
        cpu_utilization=cpu_utilization,
        memory_utilization=memory_utilization,
    )