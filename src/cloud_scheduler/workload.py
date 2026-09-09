import random

from cloud_scheduler.domain.job import Job


def generate_jobs(
    count: int,
    seed: int = 42,
) -> list[Job]:
    """Tekrarlanabilir özelliklere sahip yeni deneme görevleri üretir."""

    if count <= 0:
        raise ValueError("Job count must be greater than zero.")

    # Bu üreticiye özel rastgele sayı kaynağı oluştur.
    random_generator = random.Random(seed)

    jobs: list[Job] = []

    for index in range(count):
        required_cpu = random_generator.choice([1, 2, 4, 8])

        required_memory_gb = random_generator.choice(
            [2.0, 4.0, 8.0, 16.0]
        )

        duration_steps = random_generator.randint(1, 6)

        job = Job(
            job_id=f"job-{index + 1}",
            required_cpu=required_cpu,
            required_memory_gb=required_memory_gb,
            duration_steps=duration_steps,
        )

        jobs.append(job)

    return jobs