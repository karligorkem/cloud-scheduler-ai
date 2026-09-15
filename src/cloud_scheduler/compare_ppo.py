from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
import csv

from cloud_scheduler.gym_environment import CloudSchedulerEnv


def choose_rule_action(
    env: CloudSchedulerEnv,
    algorithm: str,
) -> int:
    """First Fit veya Best Fit kuralına göre geçerli eylem seçer."""

    mask = env.action_masks()
    wait_action = len(mask) - 1

    if algorithm == "First Fit":
        for server_index in range(wait_action):
            if mask[server_index]:
                return server_index

        return wait_action

    if algorithm != "Best Fit":
        raise ValueError("Unknown rule-based algorithm.")

    # Mevcut Best Fit gibi, atama sonrası en az boş CPU bırakanı seç.
    simulation = env.environment.simulation
    job = simulation.queue.peek()

    if job is None:
        return wait_action

    selected_action = wait_action
    smallest_remaining_cpu = None

    for server_index, server in enumerate(simulation.cluster.servers):
        if not mask[server_index]:
            continue

        remaining_cpu = server.available_cpu - job.required_cpu

        if (
            smallest_remaining_cpu is None
            or remaining_cpu < smallest_remaining_cpu
        ):
            selected_action = server_index
            smallest_remaining_cpu = remaining_cpu

    return selected_action


def run_experiment(
    algorithm: str,
    seed: int,
    model: MaskablePPO,
) -> dict:
    """Bir algoritmayı temiz ortamda çalıştırıp sonuçlarını döndürür."""

    env = CloudSchedulerEnv(max_decisions=1000)

    try:
        observation, info = env.reset(seed=seed)
        workload_seed = info["episode_seed"]

        total_reward = 0.0

        while True:
            if algorithm == "PPO":
                action, _ = model.predict(
                    observation,
                    action_masks=env.action_masks(),
                    deterministic=True,
                )

                action = int(np.asarray(action).item())
            else:
                action = choose_rule_action(env, algorithm)

            observation, reward, terminated, truncated, info = (
                env.step(action)
            )

            total_reward = total_reward + reward

            if terminated or truncated:
                break

        completed_jobs = env.environment.simulation.completed_jobs

        average_waiting = None

        if terminated and completed_jobs:
            total_waiting = 0

            for job in completed_jobs:
                waiting = job.waiting_steps

                if waiting is None:
                    raise ValueError("Completed job is missing timing.")

                total_waiting = total_waiting + waiting

            average_waiting = total_waiting / len(completed_jobs)

            if total_reward != -total_waiting:
                raise ValueError("Reward and waiting time do not match.")

        return {
            "algorithm": algorithm,
            "seed": seed,
            "workload_seed": workload_seed,
            "completed_count": len(completed_jobs),
            "terminated": terminated,
            "truncated": truncated,
            "elapsed_steps": info["current_step"],
            "total_reward": total_reward,
            "average_waiting": average_waiting,
        }

    finally:
        env.close()

def main() -> None:
    model_path = Path("outputs/ppo_long_run/scheduler_ppo.zip")

    if not model_path.is_file():
        raise FileNotFoundError(f"Model bulunamadi: {model_path}")

    model = MaskablePPO.load(str(model_path), device="cpu")

    all_results = []

    for seed in range (2000, 2020):
        print(f"\n{'=' * 55}")
        print(f"ORTAM SEED: {seed}")
        print("=" * 55)

        scenario_results = []

        for algorithm in ["First Fit", "Best Fit", "PPO"]:
            result = run_experiment(
                algorithm=algorithm,
                seed=seed,
                model=model,
            )

            scenario_results.append(result)
            all_results.append(result)

            waiting = result["average_waiting"]

            if waiting is None:
                waiting_text = "hesaplanmadi"
            else:
                waiting_text = f"{waiting:.2f}"

            print(
                f"{algorithm}"
                f" | Tamamlanan: {result['completed_count']}/20"
                f" | Bitti: {result['terminated']}"
                f" | Zaman: {result['elapsed_steps']}"
                f" | Bekleme: {waiting_text}"
                f" | Odul: {result['total_reward']:.2f}"
            )

        workload_seeds = {
            result["workload_seed"] for result in scenario_results
        }

        if len(workload_seeds) != 1:
            raise ValueError("Algorithms used different workload seeds.")

    output_path = Path(
        "outputs/ppo_first_run/comparison_20_scenarios.csv"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "algorithm",
        "seed",
        "workload_seed",
        "completed_count",
        "terminated",
        "truncated",
        "elapsed_steps",
        "total_reward",
        "average_waiting",
    ]

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nKarsilastirma kaydedildi: {output_path.resolve()}")

    if len(workload_seeds) != 1:
            raise ValueError("Algorithms used different workload seeds.")


if __name__ == "__main__":
    main()