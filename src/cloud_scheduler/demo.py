from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def main() -> None:
    # 1. Sunucuların bulunacağı kümeyi oluştur.
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    # 2. Çalıştırılacak görevleri oluştur.
    first_job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=2,
    )

    second_job = Job(
        job_id="job-2",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    # 3. Görevleri bekleme sırasına ekle.
    queue = JobQueue()
    queue.add(first_job)
    queue.add(second_job)

    # 4. Yerleştirme algoritmasını oluştur.
    scheduler = FirstFitScheduler()

    # 5. Hazırladığımız parçaları simülasyona ver.
    simulation = Simulation(
        cluster=cluster,
        queue=queue,
        scheduler=scheduler,
    )

    # 6. Simülasyonu en fazla 10 adım çalıştır.
    completed_jobs = simulation.run(max_steps=10)

    # 7. Sonuçları terminale yazdır.
    print(f"Gecen zaman adimi: {cluster.current_step}")
    print(f"Tamamlanan gorev sayisi: {len(completed_jobs)}")

    for job in completed_jobs:
        print(
            f"Gorev: {job.job_id}"
            f" | Sunucu: {job.assigned_server_id}"
            f" | Durum: {job.status.value}"
        )

    if simulation.is_finished():
        print("Butun gorevler tamamlandi.")
    else:
        print("Adim sinirina ulasildi; tamamlanmamis gorevler var.")


if __name__ == "__main__":
    main()