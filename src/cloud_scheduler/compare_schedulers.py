import csv
from pathlib import Path

from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.base import Scheduler
from cloud_scheduler.schedulers.best_fit import BestFitScheduler
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation
from cloud_scheduler.workload import generate_jobs


def create_scenario(
    job_count: int,
    seed: int,
) -> tuple[Cluster, JobQueue]:
    """Her deney için yeni sunucular ve görevler oluşturur."""

    cluster = Cluster()

    cluster.add_server(
        Server(
            server_id="large-server",
            total_cpu=8,
            total_memory_gb=16.0,
        )
    )

    cluster.add_server(
        Server(
            server_id="small-server",
            total_cpu=4,
            total_memory_gb=8.0,
        )
    )

    jobs = generate_jobs(count=job_count, seed=seed)

    queue = JobQueue()

    for job in jobs:
        queue.add(job)

    return cluster, queue


def run_experiment(
    name: str,
    scheduler: Scheduler,
    job_count: int,
    seed: int,
) -> dict[str, str | int | float | bool | None]:
    """Bir deney çalıştırır ve ölçümlerini sözlük olarak döndürür."""

    cluster, queue = create_scenario(
        job_count=job_count,
        seed=seed,
    )

    simulation = Simulation(
        cluster=cluster,
        queue=queue,
        scheduler=scheduler,
    )

    completed_jobs = simulation.run(max_steps=1000)
    finished = simulation.is_finished()

    result: dict[str, str | int | float | bool | None] = {
        "scheduler": name,
        "seed": seed,
        "job_count": job_count,
        "completed_count": len(completed_jobs),
        "finished": finished,
        "elapsed_steps": cluster.current_step,
        "average_waiting_steps": None,
        "max_waiting_steps": None,
        "average_turnaround_steps": None,
    }

    # Yarım kalan deneyde tam iş yüküne ait ortalama yayımlama.
    if not finished or not completed_jobs:
        return result

    total_waiting_steps = 0
    total_turnaround_steps = 0
    max_waiting_steps = 0

    for job in completed_jobs:
        waiting_steps = job.waiting_steps
        turnaround_steps = job.turnaround_steps

        if waiting_steps is None or turnaround_steps is None:
            raise ValueError("Completed job is missing timing information.")

        total_waiting_steps = total_waiting_steps + waiting_steps
        total_turnaround_steps = total_turnaround_steps + turnaround_steps

        if waiting_steps > max_waiting_steps:
            max_waiting_steps = waiting_steps

    completed_count = len(completed_jobs)

    result["average_waiting_steps"] = (
        total_waiting_steps / completed_count
    )

    result["max_waiting_steps"] = max_waiting_steps

    result["average_turnaround_steps"] = (
        total_turnaround_steps / completed_count
    )

    return result


def main() -> None:
    job_count = 20
    seeds = [10, 20, 30, 40, 50]

    results = []

    for seed in seeds:
        first_fit_result = run_experiment(
            name="First Fit",
            scheduler=FirstFitScheduler(),
            job_count=job_count,
            seed=seed,
        )

        best_fit_result = run_experiment(
            name="Best Fit",
            scheduler=BestFitScheduler(),
            job_count=job_count,
            seed=seed,
        )

        results.append(first_fit_result)
        results.append(best_fit_result)

        print(f"\nSeed: {seed}")

        for result in [first_fit_result, best_fit_result]:
            print(
                f"{result['scheduler']}"
                f" | Tamamlanan: {result['completed_count']}/{job_count}"
                f" | Bitti: {result['finished']}"
                f" | Zaman: {result['elapsed_steps']}"
                f" | Ortalama bekleme: {result['average_waiting_steps']}"
            )

    output_path = Path("data/processed/scheduler_comparison.csv")

    # Klasör yoksa oluştur.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scheduler",
        "seed",
        "job_count",
        "completed_count",
        "finished",
        "elapsed_steps",
        "average_waiting_steps",
        "max_waiting_steps",
        "average_turnaround_steps",
    ]

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(results)

    print(f"\nSonuclar kaydedildi: {output_path.resolve()}")


if __name__ == "__main__":
    main()