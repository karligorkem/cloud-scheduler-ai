from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.base import Scheduler
from cloud_scheduler.schedulers.best_fit import BestFitScheduler
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def create_scenario() -> tuple[Cluster, JobQueue]:
    """Her çağrıda aynı özelliklerde, yeni bir senaryo oluşturur."""

    cluster = Cluster()

    large_server = Server(
        server_id="large-server",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    small_server = Server(
        server_id="small-server",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(large_server)
    cluster.add_server(small_server)

    small_job = Job(
        job_id="small-job",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
    )

    large_job = Job(
        job_id="large-job",
        required_cpu=8,
        required_memory_gb=16.0,
        duration_steps=2,
    )

    queue = JobQueue()
    queue.add(small_job)
    queue.add(large_job)

    return cluster, queue


def run_experiment(name: str, scheduler: Scheduler) -> None:
    """Verilen algoritmayı yeni bir senaryoda çalıştırıp sonucu gösterir."""

    cluster, queue = create_scenario()

    simulation = Simulation(
        cluster=cluster,
        queue=queue,
        scheduler=scheduler,
    )

    completed_jobs = simulation.run(max_steps=20)

    print(f"\nAlgoritma: {name}")
    print(f"Gecen zaman: {cluster.current_step} adim")
    print(f"Tamamlanan gorev: {len(completed_jobs)}")

    # Bitmemiş bir deneyin sonucunu tam sonuç gibi değerlendirme.
    if not simulation.is_finished():
        print("Deney tamamlanamadi: adim sinirina ulasildi.")
        return

    total_waiting_steps = 0

    for job in completed_jobs:
        waiting_steps = job.waiting_steps

        # Bu deneyde tamamlanan her görevin başlama zamanı bilinmeli.
        if waiting_steps is None:
            raise ValueError("Completed job is missing its start time.")

        total_waiting_steps = total_waiting_steps + waiting_steps

        print(
            f"{job.job_id}"
            f" | Sunucu: {job.assigned_server_id}"
            f" | Baslama: {job.started_step}"
            f" | Bitis: {job.completed_step}"
            f" | Bekleme: {waiting_steps}"
        )

    if not completed_jobs:
        print("Ortalama bekleme hesaplanamadi: tamamlanan gorev yok.")
        return

    average_waiting_steps = total_waiting_steps / len(completed_jobs)

    print(f"Ortalama bekleme: {average_waiting_steps:.2f} adim")


def main() -> None:
    run_experiment("First Fit", FirstFitScheduler())
    run_experiment("Best Fit", BestFitScheduler())


if __name__ == "__main__":
    main()