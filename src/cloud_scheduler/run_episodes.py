from cloud_scheduler.decision_environment import DecisionEnvironment
from cloud_scheduler.scenario import create_simulation


def choose_action(action_mask: tuple[bool, ...]) -> int:
    """İlk uygun sunucuyu seçer; hiçbiri uygun değilse bekler."""

    wait_action = len(action_mask) - 1

    for server_index in range(wait_action):
        if action_mask[server_index]:
            return server_index

    return wait_action


def main() -> None:
    seeds = [10, 20, 30, 40, 50]

    environment = DecisionEnvironment(
        simulation=create_simulation(seed=seeds[0]),
        simulation_factory=create_simulation,
        max_decisions=1000,
    )

    for seed in seeds:
        # Yeni görevler, boş sunucular ve sıfırlanmış sayaçlarla başla.
        initial_observation = environment.reset(seed=seed)

        total_reward = 0.0
        terminated = environment.simulation.is_finished()
        truncated = False

        while not environment.closed:
            action_mask = environment.action_masks()
            action = choose_action(action_mask)

            result = environment.step(action)

            total_reward = total_reward + result.reward
            terminated = result.terminated
            truncated = result.truncated

        simulation = environment.simulation
        completed_jobs = simulation.completed_jobs

        print(f"\nSeed: {seed}")
        print(f"Gozlem uzunlugu: {len(initial_observation)}")
        print(f"Karar sayisi: {environment.decision_count}")
        print(f"Gecen zaman: {simulation.cluster.current_step}")
        print(f"Tamamlanan gorev: {len(completed_jobs)}")
        print(f"Tamamlandi: {terminated}")
        print(f"Sinirda durdu: {truncated}")
        print(f"Toplam odul: {total_reward:.2f}")

        # Yarım kalan deneyi, tamamlanmış deney gibi değerlendirme.
        if not terminated:
            print("Deney tamamlanmadigi icin bekleme esitligi kontrol edilmedi.")
            continue

        total_waiting_steps = 0

        for job in completed_jobs:
            waiting_steps = job.waiting_steps

            if waiting_steps is None:
                raise ValueError("Completed job is missing its start time.")

            total_waiting_steps = total_waiting_steps + waiting_steps

        if not completed_jobs:
            print("Ortalama bekleme hesaplanamadi: gorev yok.")
            continue

        average_waiting_steps = (
            total_waiting_steps / len(completed_jobs)
        )

        print(f"Toplam bekleme: {total_waiting_steps}")
        print(f"Ortalama bekleme: {average_waiting_steps:.2f}")

        # Mevcut ödül tanımının bekleme kayıtlarıyla tutarlı olması gerekir.
        if total_reward != -total_waiting_steps:
            raise ValueError("Total reward does not match total waiting time.")

        print("Odul ve bekleme kontrolu: OK")


if __name__ == "__main__":
    main()