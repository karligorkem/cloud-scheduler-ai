# Cloud Scheduler AI

CPU, RAM ve GPU kaynakları sınırlı sunuculara görev yerleştirmek için
klasik zamanlama algoritmalarını ve pekiştirmeli öğrenmeyi karşılaştıran
Python projesi.

Proje, sentetik görevlerle çalışan bir simülasyon ortamı içerir.
Agent, sıradaki görevi uygun bir sunucuya atamayı veya zamanın
ilerlemesini beklemeyi öğrenir.

## Amaç

Görevlerin kaynak kısıtlarını ihlal etmeden tamamlanmasını sağlamak
ve kuyrukta geçirdikleri süreyi azaltmak.

Karşılaştırılan yöntemler:

- **First Fit:** İlk uygun sunucuyu seçer.
- **Best Fit:** Atama sonrasında en az boş CPU kalacak sunucuyu seçer.
- **Best Fit RAM:** CPU eşitliğinde daha az boş RAM kalacak sunucuyu seçer.
- **PPO:** Mevcut kaynaklar ve sıradaki görev üzerinden karar verir.
- **PPO Queue:** Ek olarak kuyruktaki ilk üç görevin kaynak ihtiyaçlarını görür.

## Sistem Nasıl Çalışır?

1. Seed kullanılarak tekrarlanabilir görevler üretilir.
2. Görevler geliş zamanlarında kuyruğa alınır.
3. Agent, uygun bir sunucuya atama veya bekleme eylemini seçer.
4. Atanan görevin CPU, RAM ve GPU kaynakları ayrılır.
5. Bekleme eylemi simülasyonu bir zaman adımı ilerletir.
6. Tamamlanan görevlerin kaynakları serbest bırakılır.
7. Bekleme süreleri, ödüller ve tamamlanma durumu kaydedilir.

Kuyruk FIFO düzenindedir. Agent yalnızca kuyruğun başındaki görevi
atayabilir; sonraki görevleri öne alamaz.

## Pekiştirmeli Öğrenme Ortamı

Ortam Gymnasium arayüzünü kullanır. Model, `sb3-contrib` içindeki
MaskablePPO ile eğitilir.

### Gözlem

İki sunuculu temel ortam 14 sayılık gözlem üretir:

- Her sunucunun aktiflik durumu ve boş CPU, RAM, GPU kaynakları.
- Kuyruk uzunluğu.
- Sıradaki görevin varlığı, kaynak ihtiyaçları ve bekleme süresi.

Kuyruk bilgili ortam, ilk üç görev için toplam 12 sayı ekler.
Bu ortamın gözlem boyutu 26'dır. İlk görev bilgisi bu sürümde
hem temel gözlemde hem kuyruk önizlemesinde bulunur.

Henüz gelmemiş görevler modele gösterilmez.

### Eylemler

İki sunuculu ortamda üç eylem bulunur:

- İlk sunucuya ata.
- İkinci sunucuya ata.
- Bekle.

Eylem maskesi, kaynakların yetmediği veya görevin atanamayacağı
sunucuları seçim dışı bırakır.

### Ödül

- Atama eylemi: `0`
- Bekleme eylemi: `-kuyruk_uzunluğu`

Tamamlanan bir deneyde indirgenmemiş toplam ödül,
görevlerin toplam bekleme süresinin negatifine eşittir.

Atama zamanı ilerletmez. Bekleme eylemi zamanı bir adım ilerletir.
Bu nedenle eğitimdeki karar sayısı ile simülasyon süresi farklıdır.

## Son Değerlendirme

Varsayılan sentetik senaryoda 6000–6099 seed aralığındaki
100 deney değerlendirilmiştir. Her deney 20 görev içerir.
Yöntemler aynı görev üretim seed'leriyle çalıştırılmıştır.

| Yöntem | Ortalama bekleme (adım) ↓ | Tamamlanan senaryo |
|---|---:|---:|
| First Fit | 14.5425 | 100/100 |
| Best Fit | 13.2990 | 100/100 |
| Best Fit RAM | 13.2930 | 100/100 |
| PPO | 13.2940 | 100/100 |
| PPO Queue | 13.2940 | 100/100 |

PPO, First Fit'e göre ortalama beklemeyi yaklaşık **%8,59** azaltmıştır.
Best Fit tabanlı yöntemlere karşı belirgin bir üstünlük gözlenmemiştir.

PPO Queue, Best Fit RAM'e göre:

- 1 senaryoda daha iyi,
- 98 senaryoda eşit,
- 1 senaryoda daha kötü sonuç vermiştir.

Ortalama fark **+0.0010 adım** olmuştur.
Kuyruk bilgisinin genişletilmesi bu değerlendirmede ortalama
performansı iyileştirmemiştir.

Bu sonuçlar değerlendirilen model dosyalarına ve senaryo yapılandırmasına
aittir. Birden fazla bağımsız eğitim seed'iyle istatistiksel
üstünlük gösterilmemiştir.

## Kurulum

Python 3.11 veya üzeri gerekir.

Windows CMD:

```bat
git clone https://github.com/karligorkem/cloud-scheduler-ai.git
cd cloud-scheduler-ai
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev,rl]"
```

## Testler

```bat
python -m pytest -q
```

Testler; kaynak yönetimini, görev yaşam döngüsünü, kuyruk davranışını,
simülasyon zamanını, eylem kısıtlarını ve gözlem üretimini kapsar.

## Model Eğitimi

14 girdili PPO:

```bat
python -m cloud_scheduler.train_ppo_long
```

26 girdili kuyruk bilgili PPO:

```bat
python -m cloud_scheduler.train_ppo_queue
```

Kuyruk bilgili eğitim betiği, hedef konumda model varsa üzerine
yazmayı reddeder.

Model dosyaları:

```text
outputs/ppo_long_run/scheduler_ppo.zip
outputs/ppo_queue_run/scheduler_ppo.zip
```

Modeller farklı gözlem boyutlarına sahip olduğundan kendi ortamlarıyla
kullanılmalıdır.

## Değerlendirmeyi Çalıştırma

Önce iki modelin eğitimini tamamlayın:

```bat
python -m cloud_scheduler.final_evaluation
```

Sonuç dosyası:

```text
outputs/final_evaluation/default_100.csv
```

CSV; yöntem, senaryo seed'i, görev üretim seed'i, tamamlanma durumu,
ortalama bekleme ve model yolunu içerir.

Model dosyaları ve üretilen deney çıktıları Git deposuna dahil değildir.
Yeniden eğitim, kütüphane sürümleri ve çalışma ortamına bağlı olarak
raporlanan değerlerden farklı sonuçlar üretebilir.

## Temel Bileşenler

| Bileşen | Sorumluluk |
|---|---|
| `domain/` | Görev, sunucu, küme ve kuyruk modelleri |
| `schedulers/` | Klasik zamanlama algoritmaları |
| `simulation.py` | Görev gelişleri ve zamanın ilerletilmesi |
| `action_executor.py` | Agent eylemlerinin uygulanması |
| `action_mask.py` | Geçerli eylemlerin belirlenmesi |
| `reward.py` | Beklemeye dayalı ödül |
| `gym_environment.py` | Temel Gymnasium ortamı |
| `queue_encoder.py` | İlk üç görevin sayısal temsili |
| `queue_gym_environment.py` | 26 girdili ortam |
| `final_evaluation.py` | Beş yöntemin ortak değerlendirmesi |

## Sınırlar

- Gerçek bulut altyapısı yerine simülasyon kullanılır.
- Görevler sentetik olarak üretilir.
- Son değerlendirme iki sunuculu varsayılan senaryoyla sınırlıdır.
- Mevcut görev üretimi GPU gerektiren işler üretmez;
  GPU kaynak kontrolü altyapıda bulunur.
- Agent görev sırasını değiştiremez.
- Gerçek donanım kullanımı, enerji tüketimi ve bulut maliyeti ölçülmez.
- Ek kuyruk bilgisi ve karma senaryolu eğitim, yapılan deneylerde
  belirgin performans artışı sağlamamıştır.

## Kullanılan Teknolojiler

Python, NumPy, PyTorch, Gymnasium, Stable-Baselines3,
sb3-contrib ve pytest.