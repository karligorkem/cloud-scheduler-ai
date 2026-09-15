import csv
from pathlib import Path

from sb3_contrib import MaskablePPO

from cloud_scheduler.compare_queue_models import run_episode
from cloud_scheduler.compare_scenarios import run_experiment
from cloud_scheduler.queue_gym_environment import QueueAwareCloudSchedulerEnv
from cloud_scheduler.scenario_config import ScenarioConfig


def main() -> None:
    old_model_path = Path("outputs/ppo_long_run/scheduler_ppo.zip")
    queue_model_path = Path("outputs/ppo_queue_run/scheduler_ppo.zip")

    for path in (old_model_path, queue_model_path):
        if not path.is_file():
            raise FileNotFoundError(f"Model bulunamadi: {path}")

    old_model = MaskablePPO.load(str(old_model_path), device="cpu")
    queue_model = MaskablePPO.load(str(queue_model_path), device="cpu")

    config = ScenarioConfig()
    seeds = range(6000, 6100)

    methods = (
        "First Fit",
        "Best Fit",
        "Best Fit RAM",
        "PPO",
        "PPO Queue",
    )

    output_path = Path("outputs/final_evaluation/default_100.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "algorithm",
        "seed",
        "workload_seed",
        "job_count",
        "completed_count",
        "terminated",
        "truncated",
        "average_waiting",
        "model_path",
    ]

    completed_counts = {method: 0 for method in methods}
    common_results = []

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for seed in seeds:
            results = {}

            # Mevcut değerlendirme fonksiyonunu tekrar kullanıyoruz.
            for method in methods[:-1]:
                results[method] = run_experiment(
                    model=old_model,
                    algorithm=method,
                    scenario_name="default",
                    config=config,
                    seed=seed,
                )

            results["PPO Queue"] = run_episode(
                model=queue_model,
                environment=QueueAwareCloudSchedulerEnv(
                    config=config,
                    max_decisions=2000,
                ),
                seed=seed,
            )

            workload_seeds = {
                result["workload_seed"]
                for result in results.values()
            }

            if len(workload_seeds) != 1:
                raise ValueError("Algorithms used different workload seeds.")

            all_completed = True
            scenario_waiting = {}

            for method, result in results.items():
                finished = (
                    result["terminated"]
                    and not result["truncated"]
                    and result["completed_count"] == config.job_count
                )

                completed_counts[method] += int(finished)

                if finished:
                    waiting = result["average_waiting"]

                    if waiting is None:
                        raise ValueError("Completed episode has no waiting time.")

                    scenario_waiting[method] = waiting
                else:
                    all_completed = False

                if method == "PPO":
                    model_path = str(old_model_path)
                elif method == "PPO Queue":
                    model_path = str(queue_model_path)
                else:
                    model_path = ""

                writer.writerow(
                    {
                        "algorithm": method,
                        "seed": seed,
                        "workload_seed": result["workload_seed"],
                        "job_count": config.job_count,
                        "completed_count": result["completed_count"],
                        "terminated": result["terminated"],
                        "truncated": result["truncated"],
                        "average_waiting": result["average_waiting"],
                        "model_path": model_path,
                    }
                )

            if all_completed:
                common_results.append(scenario_waiting)

            # Her tamamlanan seed'in sonuçlarını diske aktar.
            file.flush()

            print(f"Seed {seed} tamamlandi.")

    print()
    print("SON DEGERLENDIRME")
    print(f"Ortak tamamlanan: {len(common_results)}/{len(seeds)}")

    for method in methods:
        print(
            f"{method} tamamlanan: "
            f"{completed_counts[method]}/{len(seeds)}"
        )

    if not common_results:
        print("Ortak tamamlanan senaryo yok.")
        print(f"Sonuclar kaydedildi: {output_path}")
        return

    print()
    print("ORTAK SENARYOLARDA ORTALAMA BEKLEME")

    for method in methods:
        average = sum(
            result[method] for result in common_results
        ) / len(common_results)

        print(f"{method}: {average:.4f}")

    print()
    print("PPO QUEUE - BEST FIT RAM")

    better = 0
    equal = 0
    worse = 0
    differences = []

    for result in common_results:
        difference = result["PPO Queue"] - result["Best Fit RAM"]
        differences.append(difference)

        if abs(difference) <= 1e-9:
            equal += 1
        elif difference < 0:
            better += 1
        else:
            worse += 1

    print(f"Daha iyi: {better}")
    print(f"Esit: {equal}")
    print(f"Daha kotu: {worse}")
    print(f"Ortalama fark: {sum(differences) / len(differences):+.4f} adim")
    print()
    print(f"Sonuclar kaydedildi: {output_path}")


if __name__ == "__main__":
    main()