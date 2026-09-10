from cloud_scheduler.action_executor import ActionExecutor
from cloud_scheduler.action_mask import build_action_mask
from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.observation import (
    SchedulerObservation,
    build_observation,
)
from cloud_scheduler.observation_encoder import ObservationEncoder
from cloud_scheduler.reward import calculate_reward
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation


def choose_action(
    observation: SchedulerObservation,
    action_mask: tuple[bool, ...],
) -> int:
    """İlk uygun sunucuyu seçer; uygun sunucu yoksa bekler."""

    # Bekleme eylemi, sunucu indekslerinden sonra gelir.
    wait_action = len(observation.servers)

    if observation.next_job is None:
        return wait_action

    for server_index in range(len(observation.servers)):
        if action_mask[server_index]:
            return server_index

    return wait_action


def main() -> None:
    # 1. Sunucuyu ve kümeyi oluştur.
    cluster = Cluster()

    cluster.add_server(
        Server(
            server_id="server-1",
            total_cpu=4,
            total_memory_gb=8.0,
        )
    )

    # 2. Farklı zamanlarda gelecek iki görev oluştur.
    first_job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=2,
        arrival_step=0,
    )

    second_job = Job(
        job_id="job-2",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
        arrival_step=1,
    )

    # 3. Görevleri simülasyona teslim et.
    simulation = Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=[first_job, second_job],
    )

    # İlk karar öncesinde zamanı gelen görevleri kabul eder.
    executor = ActionExecutor(simulation)

    # Gözlemi sabit sırada sayılara dönüştürür.
    encoder = ObservationEncoder(
        server_count=len(cluster.servers),
    )

    max_decisions = 20
    total_reward = 0.0

    # 4. Gözlem → karar → eylem → ödül döngüsü.
    for decision_number in range(1, max_decisions + 1):
        if simulation.is_finished():
            break

        # Karar öncesindeki sistem durumunu al.
        observation = build_observation(
            simulation.cluster,
            simulation.queue,
        )

        observation_vector = encoder.encode(observation)

        # Hangi seçimlerin geçerli olduğunu belirle.
        action_mask = build_action_mask(
            simulation.cluster,
            simulation.queue,
        )

        # Şimdilik öğrenmeyen, basit bir politika kullanıyoruz.
        action = choose_action(observation, action_mask)

        print(
            f"\nKarar: {decision_number}"
            f" | Zaman: {observation.current_step}"
            f" | Kuyruk: {observation.queue_length}"
        )

        print(f"Gozlem vektoru: {observation_vector}")
        print(f"Gecerli eylemler: {action_mask}")

        wait_action = len(observation.servers)

        if action == wait_action:
            print("Eylem: bir adim bekle")
        else:
            selected_server = observation.servers[action]

            print(
                f"Eylem: siradaki gorevi "
                f"{selected_server.server_id} sunucusuna ata"
            )

        # Seçilen eylemi gerçek simülasyon durumuna uygula.
        completed_jobs = executor.apply(action)

        # Başarılı eylemin ödülünü eski gözlemden hesapla.
        reward = calculate_reward(observation, action)
        total_reward = total_reward + reward

        print(
            f"Odul: {reward:.1f}"
            f" | Toplam odul: {total_reward:.1f}"
        )

        for job in completed_jobs:
            print(
                f"Tamamlandi: {job.job_id}"
                f" | Zaman: {job.completed_step}"
            )

    # 5. Deneyin sonucunu göster.
    if not simulation.is_finished():
        print("\nKarar sinirina ulasildi; tamamlanmamis gorevler var.")
        print(f"Toplam odul: {total_reward:.1f}")
        return

    print("\nButun gorevler tamamlandi.")
    print(f"Toplam odul: {total_reward:.1f}")

    for job in simulation.completed_jobs:
        print(
            f"{job.job_id}"
            f" | Gelis: {job.arrival_step}"
            f" | Baslama: {job.started_step}"
            f" | Bitis: {job.completed_step}"
            f" | Bekleme: {job.waiting_steps}"
        )


if __name__ == "__main__":
    main()