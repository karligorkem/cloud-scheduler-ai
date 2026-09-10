import random

from cloud_scheduler.domain.job import Job


def generate_jobs(
    count: int,
    seed: int = 42,
    max_arrival_step: int = 0,
) -> list[Job]:
    """Tekrarlanabilir görevler ve geliş zamanları üretir."""

    if count <= 0:
        raise ValueError("Job count must be greater than zero.")

    if max_arrival_step < 0:
        raise ValueError("Max arrival step cannot be negative.")

    resource_generator = random.Random(seed)
    arrival_generator = random.Random(seed + 1)

    jobs: list[Job] = []

    for index in range(count):
        required_cpu = resource_generator.choice([1, 2, 4, 8])

        required_memory_gb = resource_generator.choice(
            [2.0, 4.0, 8.0, 16.0]
        )

        duration_steps = resource_generator.randint(1, 6)

        arrival_step = arrival_generator.randint(
            0,
            max_arrival_step,
        )

        job = Job(
            job_id=f"job-{index + 1}",
            required_cpu=required_cpu,
            required_memory_gb=required_memory_gb,
            duration_steps=duration_steps,
            arrival_step=arrival_step,
        )

        jobs.append(job)

    return jobs