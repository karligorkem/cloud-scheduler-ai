from cloud_scheduler.observation import SchedulerObservation


def calculate_reward(
    observation: SchedulerObservation,
    action: int,
) -> float:
    """Geçerli bir eylemin kuyrukta bekleme maliyetini hesaplar."""

    wait_action = len(observation.servers)

    if action == wait_action:
        return -float(observation.queue_length)

    return 0.0