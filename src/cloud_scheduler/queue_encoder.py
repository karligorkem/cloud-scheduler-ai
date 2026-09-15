from cloud_scheduler.domain.job_queue import JobQueue


def encode_queue_preview(
    queue: JobQueue,
    max_jobs: int = 3,
) -> tuple[float, ...]:
    """Kuyruktaki ilk görevlerin kaynak ihtiyaçlarını sayılara dönüştürür."""

    if max_jobs <= 0:
        raise ValueError("Max jobs must be greater than zero.")

    # Mevcut gözlem kodlayıcısıyla aynı ölçekleri kullanıyoruz.
    cpu_scale = 8.0
    memory_scale = 16.0
    gpu_scale = 1.0

    encoded_values: list[float] = []

    for index in range(max_jobs):
        # Bu sırada bir görev yoksa dört sıfır ekle.
        if index >= len(queue.jobs):
            encoded_values.extend([0.0, 0.0, 0.0, 0.0])
            continue

        job = queue.jobs[index]

        encoded_values.extend(
            [
                1.0,
                job.required_cpu / cpu_scale,
                job.required_memory_gb / memory_scale,
                job.required_gpu_count / gpu_scale,
            ]
        )

    return tuple(encoded_values)