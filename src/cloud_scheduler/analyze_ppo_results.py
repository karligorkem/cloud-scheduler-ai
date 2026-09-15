import csv
from math import isclose
from pathlib import Path


def main() -> None:
    input_path = Path(
        "outputs/ppo_first_run/comparison_100_scenarios.csv"
    )
    results_by_seed = {}

    with input_path.open(
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        for row in csv.DictReader(file):
            seed = int(row["seed"])
            algorithm = row["algorithm"]

            if seed not in results_by_seed:
                results_by_seed[seed] = {}

            if algorithm in results_by_seed[seed]:
                raise ValueError(
                    f"Tekrarlanan sonuc: seed={seed}, algorithm={algorithm}"
                )

            results_by_seed[seed][algorithm] = row

    better_count = 0
    equal_count = 0
    worse_count = 0
    skipped_count = 0

    differences = []

    for seed in sorted(results_by_seed):
        scenario = results_by_seed[seed]

        if "PPO" not in scenario or "Best Fit" not in scenario:
            raise ValueError(f"Seed {seed}: PPO veya Best Fit sonucu eksik.")

        ppo = scenario["PPO"]
        best_fit = scenario["Best Fit"]

        if ppo["workload_seed"] != best_fit["workload_seed"]:
            raise ValueError(f"Seed {seed}: gorev seed'leri farkli.")

        pair_completed = all(
            row["terminated"] == "True"
            and row["truncated"] == "False"
            and int(row["completed_count"]) == 20
            for row in [ppo, best_fit]
        )

        if not pair_completed:
            skipped_count = skipped_count + 1
            continue

        ppo_waiting = float(ppo["average_waiting"])
        best_fit_waiting = float(best_fit["average_waiting"])

        difference = ppo_waiting - best_fit_waiting

        # Yalnızca çok küçük hesaplama farklarını eşit kabul et.
        if isclose(difference, 0.0, rel_tol=0.0, abs_tol=1e-9):
            difference = 0.0
            equal_count = equal_count + 1
        elif difference < 0:
            better_count = better_count + 1
        else:
            worse_count = worse_count + 1

        differences.append((seed, difference))

    compared_count = len(differences)

    print(f"Karsilastirilan senaryo: {compared_count}")
    print(f"Tamamlanmadigi icin atlanan: {skipped_count}")

    if compared_count == 0:
        print("Karsilastirilabilecek sonuc yok.")
        return

    print("\nPPO'NUN BEST FIT'E GORE DURUMU")
    print(f"Daha iyi: {better_count}")
    print(f"Esit:     {equal_count}")
    print(f"Daha kotu: {worse_count}")

    total_difference = sum(
        difference for seed, difference in differences
    )

    mean_difference = total_difference / compared_count

    # Artılarla eksilerin birbirini götürmesini önleyen ikinci ölçüm.
    mean_absolute_difference = sum(
        abs(difference) for seed, difference in differences
    ) / compared_count

    print(f"\nOrtalama fark: {mean_difference:+.4f} adim")
    print(f"Ortalama mutlak fark: {mean_absolute_difference:.4f} adim")

    # En büyük farkları, işaretinden bağımsız olarak önce göster.
    largest_differences = sorted(
        differences,
        key=lambda item: abs(item[1]),
        reverse=True,
    )

    print("\nEN BUYUK FARKLAR")

    shown_count = 0

    for seed, difference in largest_differences:
        if difference == 0.0:
            continue

        print(
            f"Seed: {seed}"
            f" | PPO - Best Fit: {difference:+.2f} adim"
        )

        shown_count = shown_count + 1

        if shown_count == 5:
            break

    if shown_count == 0:
        print("Butun senaryolarda ortalama bekleme degerleri esit.")


if __name__ == "__main__":
    main()