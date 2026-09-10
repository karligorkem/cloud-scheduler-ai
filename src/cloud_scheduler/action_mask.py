from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job_queue import JobQueue


def build_action_mask(
    cluster: Cluster,
    queue: JobQueue,
) -> tuple[bool, ...]:
    """Sunucu atamalarının ve beklemenin geçerliliğini gösterir."""

    job = queue.peek()

    valid_actions: list[bool] = []

    for server in cluster.servers:
        if job is None:
            valid_actions.append(False)
        else:
            valid_actions.append(server.can_host(job))

    # Son seçim her zaman bekleme eylemidir.
    valid_actions.append(True)

    return tuple(valid_actions)