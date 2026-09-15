from pathlib import Path

from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor

from cloud_scheduler.mixed_environment import MixedScenarioEnv


def main() -> None:
    output_directory = Path("outputs/ppo_mixed_run")
    output_directory.mkdir(parents=True, exist_ok=True)

    train_env = Monitor(
        MixedScenarioEnv(max_decisions=1000),
        filename=str(output_directory / "training.monitor.csv"),
        info_keywords=("scenario", "job_count"),
    )

    try:
        model = MaskablePPO(
            policy="MlpPolicy",
            env=train_env,
            learning_rate=0.0003,
            n_steps=256,
            batch_size=64,
            n_epochs=10,
            gamma=1.0,
            ent_coef=0.01,
            seed=42,
            device="cpu",
            verbose=1,
        )

        print("Karma senaryolarla egitim basliyor.")

        model.learn(total_timesteps=102_400)

        model_path = output_directory / "scheduler_ppo"
        model.save(str(model_path))

        print(f"\nModel kaydedildi: {model_path}.zip")

    finally:
        train_env.close()


if __name__ == "__main__":
    main()