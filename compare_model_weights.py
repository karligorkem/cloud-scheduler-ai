import torch
from sb3_contrib import MaskablePPO


def main() -> None:
    # Daha önce eğittiğimiz iki modeli yükle.
    single_model = MaskablePPO.load(
        "outputs/ppo_long_run/scheduler_ppo.zip",
        device="cpu",
    )

    mixed_model = MaskablePPO.load(
        "outputs/ppo_mixed_run/scheduler_ppo.zip",
        device="cpu",
    )

    # Ağların öğrendiği ağırlıkları ve diğer kayıtlı tensörleri al.
    single_weights = single_model.policy.state_dict()
    mixed_weights = mixed_model.policy.state_dict()

    # Karşılaştırmadan önce aynı ağ yapısını kullandıklarını kontrol et.
    if single_weights.keys() != mixed_weights.keys():
        print("Modellerin ag yapilari farkli.")
        return

    different_count = 0
    largest_difference = 0.0

    for name, single_tensor in single_weights.items():
        mixed_tensor = mixed_weights[name]

        if single_tensor.shape != mixed_tensor.shape:
            print(f"Boyutlar farkli: {name}")
            return

        # İki tensörün bütün değerleri birebir aynı mı?
        if torch.equal(single_tensor, mixed_tensor):
            continue

        different_count += 1

        # Bu ağırlık grubundaki en büyük mutlak farkı bul.
        difference = (
            single_tensor.to(dtype=torch.float64)
            - mixed_tensor.to(dtype=torch.float64)
        ).abs().max().item()

        largest_difference = max(largest_difference, difference)

        print(f"Farkli grup: {name}")
        print(f"En buyuk fark: {difference:.8f}")

    print()
    print(f"Toplam agirlik grubu: {len(single_weights)}")
    print(f"Farkli agirlik grubu: {different_count}")
    print(f"Genel en buyuk fark: {largest_difference:.8f}")

    if different_count == 0:
        print("SONUC: Kayitli ag agirliklari birebir ayni.")
    else:
        print("SONUC: Kayitli ag agirliklari farkli.")


if __name__ == "__main__":
    main()