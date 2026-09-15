import csv
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.schedulers.best_fit import BestFitScheduler
from cloud_scheduler.schedulers.best_fit_ram import BestFitRamScheduler
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler


def run_experiment(
    algorithm: str,
    seed: int,
    model: MaskablePPO,
) -> dict:
    """Bir yöntemi temiz ortamda çalıştırır."""

    schedulers = {
        "First Fit": FirstFitScheduler(),
        "Best Fit": BestFitScheduler(),
        "Best Fit RAM": BestFitRamScheduler(),
    }

    env = CloudSchedulerEnv(max_decisions=1000)

    try:
        observation, info = env.reset(seed=seed)
        workload_seed = info["episode_seed"]
        total_reward = 0.0

        while True:
            if algorithm == "PPO":
                predicted_action, _ = model.predict(
                    observation,
                    action_masks=env.action_masks(),
                    deterministic=True,
                )

                action = int(np.asarray(predicted_action).item())

            else:
                simulation = env.environment.simulation
                servers = simulation.cluster.servers
                job = simulation.queue.peek()

                # Varsayılan seçim bekleme.
                action = len(servers)

                if job is not None:
                    scheduler = schedulers[algorithm]

                    selected_server = scheduler.select_server(
                        simulation.cluster,
                        job,
                    )

                    if selected_server is not None:
                        action = servers.index(selected_server)

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

            if total_reward != -total_waiting:
                raise ValueError("Reward and waiting time do not match.")

            average_waiting = total_waiting / len(completed_jobs)

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

    algorithms = ["First Fit", "Best Fit", "Best Fit RAM", "PPO"]

    all_results = []
    common_results = []
    common_scenario_count = 0

    for seed in range(3000, 3100):
        scenario_results = []

        for algorithm in algorithms:
            result = run_experiment(algorithm, seed, model)

            scenario_results.append(result)
            all_results.append(result)

        workload_seeds = {
            result["workload_seed"] for result in scenario_results
        }

        if len(workload_seeds) != 1:
            raise ValueError("Algorithms used different workload seeds.")

        all_completed = all(
            result["terminated"]
            and not result["truncated"]
            and result["completed_count"] == 20
            for result in scenario_results
        )

        if all_completed:
            common_results.extend(scenario_results)
            common_scenario_count = common_scenario_count + 1

        print(f"Seed {seed} tamamlandi | Hepsi bitirdi: {all_completed}")

    output_path = Path(
        "outputs/ppo_long_run/ram_tiebreak_100_scenarios.csv"
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

    print(f"\nCSV kaydedildi: {output_path.resolve()}")
    print(f"Ortak tamamlanan senaryo: {common_scenario_count}/100")

    print("\nYONTEM BASINA TAMAMLANAN SENARYO")

    for algorithm in algorithms:
        completed_count = sum(
            1
            for result in all_results
            if result["algorithm"] == algorithm
            and result["terminated"]
            and not result["truncated"]
            and result["completed_count"] == 20
        )

        print(f"{algorithm}: {completed_count}/100")

    if common_scenario_count == 0:
        print("Ortak tamamlanan senaryo olmadigi icin ortalama hesaplanamadi.")
        return

    print("\nORTAK SENARYOLARDA ORTALAMA BEKLEME")

    for algorithm in algorithms:
        waiting_values = [
            result["average_waiting"]
            for result in common_results
            if result["algorithm"] == algorithm
        ]

        average = sum(waiting_values) / len(waiting_values)

        print(f"{algorithm}: {average:.4f} adim")


if __name__ == "__main__":
    main()