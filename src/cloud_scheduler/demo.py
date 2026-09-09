from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def main() -> None:
    # Sunucuyu ve kümeyi oluştur.
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    # İlk görev sunucunun bütün CPU ve RAM kaynaklarını kullanır.
    first_job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=2,
    )

    # İkinci görev, ilk görev tamamlanana kadar bekler.
    second_job = Job(
        job_id="job-2",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    queue = JobQueue()
    queue.add(first_job)
    queue.add(second_job)

    scheduler = FirstFitScheduler()

    simulation = Simulation(
        cluster=cluster,
        queue=queue,
        scheduler=scheduler,
    )

    completed_jobs = simulation.run(max_steps=10)

    print(f"Gecen zaman adimi: {cluster.current_step}")
    print(f"Tamamlanan gorev sayisi: {len(completed_jobs)}")

    total_waiting_steps = 0
    measured_job_count = 0

    for job in completed_jobs:
        print(
            f"\nGorev: {job.job_id}"
            f"\nSunucu: {job.assigned_server_id}"
            f"\nBaslama zamani: {job.started_step}"
            f"\nTamamlanma zamani: {job.completed_step}"
            f"\nBekleme suresi: {job.waiting_steps}"
            f"\nSistemde gecen toplam sure: {job.turnaround_steps}"
        )

        waiting_steps = job.waiting_steps

        if waiting_steps is not None:
            total_waiting_steps = total_waiting_steps + waiting_steps
            measured_job_count = measured_job_count + 1

    if measured_job_count > 0:
        average_waiting_steps = total_waiting_steps / measured_job_count

        print(
            "\nTamamlanan ve bekleme suresi bilinen gorevlerin "
            f"ortalama beklemesi: {average_waiting_steps:.2f} adim"
        )
    else:
        print("\nOrtalama bekleme hesaplanamadi: olculebilen gorev yok.")

    if simulation.is_finished():
        print("Butun gorevler tamamlandi.")
    else:
        print("Adim sinirina ulasildi; tamamlanmamis gorevler var.")


if __name__ == "__main__":
    main()