import numpy as np

from cloud_scheduler.gym_environment import CloudSchedulerEnv


def main() -> None:
    env = CloudSchedulerEnv(max_decisions=1000)

    try:
        observation, info = env.reset(seed=42)

        print(f"Gozlem boyutu: {observation.shape}")
        print(f"Gozlem veri tipi: {observation.dtype}")
        print(f"Eylem sayisi: {env.action_space.n}")
        print(f"Gorev uretim seed'i: {info['episode_seed']}")

        total_reward = 0.0

        while True:
            # True olan eylemlerin indekslerini bul.
            valid_actions = np.flatnonzero(env.action_masks())

            # İlk uygun sunucuyu, hiçbiri uygun değilse beklemeyi seç.
            action = int(valid_actions[0])

            observation, reward, terminated, truncated, info = (
                env.step(action)
            )

            if not env.observation_space.contains(observation):
                raise ValueError("Observation is outside the defined space.")

            total_reward = total_reward + reward

            if terminated or truncated:
                break

        print(f"Tamamlandi: {terminated}")
        print(f"Sinirda durdu: {truncated}")
        print(f"Tamamlanan gorev: {info['completed_count']}")
        print(f"Gecen zaman: {info['current_step']}")
        print(f"Toplam odul: {total_reward:.2f}")

    finally:
        env.close()


if __name__ == "__main__":
    main()