from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.queue_gym_environment import QueueAwareCloudSchedulerEnv


def run_episode(
    model: MaskablePPO,
    environment: CloudSchedulerEnv,
    seed: int,
) -> dict:
    """Bir modeli belirtilen seed ile değerlendirir."""

    try:
        observation, info = environment.reset(seed=seed)
        workload_seed = info["episode_seed"]

        total_reward = 0.0

        while True:
            prediction, _ = model.predict(
                observation,
                action_masks=environment.action_masks(),
                deterministic=True,
            )

            action = int(np.asarray(prediction).item())

            observation, reward, terminated, truncated, _ = environment.step(
                action
            )

            total_reward += float(reward)

            if terminated or truncated:
                break

        simulation = environment.environment.simulation
        completed_jobs = simulation.completed_jobs

        average_waiting = None

        if terminated:
            waiting_times = []

            for job in completed_jobs:
                if job.waiting_steps is None:
                    raise ValueError("Completed job has no waiting time.")

                waiting_times.append(job.waiting_steps)

            total_waiting = sum(waiting_times)

            if not np.isclose(total_reward, -total_waiting):
                raise ValueError("Reward and waiting time do not match.")

            if waiting_times:
                average_waiting = total_waiting / len(waiting_times)

        return {
            "workload_seed": workload_seed,
            "completed_count": len(completed_jobs),
            "terminated": terminated,
            "truncated": truncated,
            "average_waiting": average_waiting,
        }

    finally:
        environment.close()


def main() -> None:
    old_path = Path("outputs/ppo_long_run/scheduler_ppo.zip")
    new_path = Path("outputs/ppo_queue_run/scheduler_ppo.zip")

    for path in (old_path, new_path):
        if not path.is_file():
            raise FileNotFoundError(f"Model bulunamadi: {path}")

    old_model = MaskablePPO.load(str(old_path), device="cpu")
    new_model = MaskablePPO.load(str(new_path), device="cpu")

    # Önceki geliştirme karşılaştırmalarındaki aynı 10 senaryo.
    seeds = range(5000, 5010)

    old_waiting_values = []
    new_waiting_values = []

    old_completed_count = 0
    new_completed_count = 0

    better_count = 0
    equal_count = 0
    worse_count = 0

    for seed in seeds:
        old_result = run_episode(
            model=old_model,
            environment=CloudSchedulerEnv(max_decisions=2000),
            seed=seed,
        )

        new_result = run_episode(
            model=new_model,
            environment=QueueAwareCloudSchedulerEnv(max_decisions=2000),
            seed=seed,
        )

        # İki ortam aynı görev üretim seed'ini kullanmalı.
        if old_result["workload_seed"] != new_result["workload_seed"]:
            raise ValueError("Models used different workload seeds.")

        old_finished = (
            old_result["terminated"]
            and not old_result["truncated"]
            and old_result["completed_count"] == 20
        )

        new_finished = (
            new_result["terminated"]
            and not new_result["truncated"]
            and new_result["completed_count"] == 20
        )

        old_completed_count += int(old_finished)
        new_completed_count += int(new_finished)

        print()
        print(f"Seed: {seed}")

        if not (old_finished and new_finished):
            print(f"Eski model tamamladi: {old_finished}")
            print(f"Yeni model tamamladi: {new_finished}")
            print("Bu senaryo ortak ortalamaya alinmadi.")
            continue

        old_waiting = old_result["average_waiting"]
        new_waiting = new_result["average_waiting"]

        if old_waiting is None or new_waiting is None:
            raise ValueError("Completed episode has no average waiting time.")

        old_waiting_values.append(old_waiting)
        new_waiting_values.append(new_waiting)

        difference = new_waiting - old_waiting

        if abs(difference) <= 1e-9:
            equal_count += 1
        elif difference < 0:
            better_count += 1
        else:
            worse_count += 1

        print(f"Eski PPO: {old_waiting:.4f}")
        print(f"Kuyruk bilgili PPO: {new_waiting:.4f}")
        print(f"Yeni - eski: {difference:+.4f} adim")

    print()
    print("GENEL SONUC")
    print(f"Eski model tamamlanan: {old_completed_count}/{len(seeds)}")
    print(f"Yeni model tamamlanan: {new_completed_count}/{len(seeds)}")
    print(f"Ortak tamamlanan: {len(old_waiting_values)}/{len(seeds)}")

    if not old_waiting_values:
        print("Ortak tamamlanan senaryo olmadigi icin ortalama hesaplanamadi.")
        return

    old_average = sum(old_waiting_values) / len(old_waiting_values)
    new_average = sum(new_waiting_values) / len(new_waiting_values)

    print(f"Eski PPO ortalama bekleme: {old_average:.4f}")
    print(f"Kuyruk bilgili PPO ortalama bekleme: {new_average:.4f}")
    print(f"Yeni model daha iyi: {better_count}")
    print(f"Esit: {equal_count}")
    print(f"Yeni model daha kotu: {worse_count}")

    if old_average > 0:
        improvement = 100 * (old_average - new_average) / old_average
        print(f"Bekleme azalmasi: %{improvement:.2f}")


if __name__ == "__main__":
    main()