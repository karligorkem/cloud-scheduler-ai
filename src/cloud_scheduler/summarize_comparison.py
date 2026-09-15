import csv
from pathlib import Path


def main() -> None:
    input_path = Path("outputs/ppo_first_run/comparison_20_scenarios.csv")

    if not input_path.is_file():
        raise FileNotFoundError(
            "Karsilastirma dosyasi bulunamadi. "
            "Once python -m cloud_scheduler.compare_ppo calistir."
        )

    results_by_seed = {}

    with input_path.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            seed = int(row["seed"])
            algorithm = row["algorithm"]

            if seed not in results_by_seed:
                results_by_seed[seed] = {}

            if algorithm in results_by_seed[seed]:
                raise ValueError(
                    f"Tekrarlanan sonuc: seed={seed}, algorithm={algorithm}"
                )

            results_by_seed[seed][algorithm] = row

    if not results_by_seed:
        raise ValueError("Karsilastirma dosyasinda sonuc yok.")

    first_fit_values = []
    best_fit_values = []
    ppo_values = []

    for seed in sorted(results_by_seed):
        scenario = results_by_seed[seed]

        required_algorithms = {"First Fit", "Best Fit", "PPO"}

        if set(scenario) != required_algorithms:
            raise ValueError(f"Seed {seed}: algoritma sonuclari eksik veya farkli.")

        workload_seeds = {
            row["workload_seed"] for row in scenario.values()
        }

        if len(workload_seeds) != 1:
            raise ValueError(f"Seed {seed}: gorev seed'leri eslesmiyor.")

        # Bu deneylerin her birinde 20 gorev bulunuyor.
        all_completed = all(
            row["terminated"] == "True"
            and row["truncated"] == "False"
            and int(row["completed_count"]) == 20
            for row in scenario.values()
        )

        print(f"\nSeed: {seed}")

        if not all_completed:
            print("En az bir algoritma tamamlayamadi.")
            print("Bu senaryo ortalama bekleme karsilastirmasina alinmadi.")
            continue

        first_fit = float(scenario["First Fit"]["average_waiting"])
        best_fit = float(scenario["Best Fit"]["average_waiting"])
        ppo = float(scenario["PPO"]["average_waiting"])

        first_fit_values.append(first_fit)
        best_fit_values.append(best_fit)
        ppo_values.append(ppo)

        print(f"First Fit: {first_fit:.2f}")
        print(f"Best Fit:  {best_fit:.2f}")
        print(f"PPO:       {ppo:.2f}")

        print(f"PPO - First Fit: {ppo - first_fit:+.2f} adim")
        print(f"PPO - Best Fit:  {ppo - best_fit:+.2f} adim")

    scenario_count = len(ppo_values)

    print(
        f"\nKarsilastirmaya alinan senaryo: "
        f"{scenario_count}/{len(results_by_seed)}"
    )

    if scenario_count == 0:
        print("Ortalama hesaplamak icin tamamlanmis ortak senaryo yok.")
        return

    first_fit_mean = sum(first_fit_values) / scenario_count
    best_fit_mean = sum(best_fit_values) / scenario_count
    ppo_mean = sum(ppo_values) / scenario_count

    print("\nORTALAMA BEKLEME")
    print(f"First Fit: {first_fit_mean:.2f}")
    print(f"Best Fit:  {best_fit_mean:.2f}")
    print(f"PPO:       {ppo_mean:.2f}")

    if first_fit_mean > 0:
        improvement = (
            (first_fit_mean - ppo_mean) / first_fit_mean
        ) * 100

        print(f"First Fit'e gore bekleme azalmasi: %{improvement:.2f}")

    if best_fit_mean > 0:
        improvement = (
            (best_fit_mean - ppo_mean) / best_fit_mean
        ) * 100

        print(f"Best Fit'e gore bekleme azalmasi: %{improvement:.2f}")


if __name__ == "__main__":
    main()