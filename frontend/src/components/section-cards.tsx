import { useSimulation } from "@/components/simulation-provider";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function SectionCards() {
  const {
    data: simulation,
    error,
    refresh,
  } = useSimulation();

  if (error) {
    return (
      <div className="mx-4 rounded-xl border border-orange-500/40 bg-orange-500/10 p-5 lg:mx-6">
        <p className="text-sm text-orange-200" role="alert">
          {error}
        </p>

        <button
          type="button"
          className="mt-4 rounded-md bg-orange-500 px-4 py-2 text-sm font-medium text-black hover:bg-orange-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-400"
          onClick={() => void refresh()}
        >
          Tekrar bağlan
        </button>
      </div>
    );
  }

  if (!simulation) {
    return (
      <div
        className="mx-4 rounded-xl border border-[#333943] bg-[#191c22] p-6 text-sm text-slate-400 lg:mx-6"
        role="status"
      >
        Simülasyon verileri yükleniyor…
      </div>
    );
  }

  const completionRate =
    simulation.total_jobs > 0
      ? (simulation.completed_count / simulation.total_jobs) * 100
      : 0;

  const episodeStatus = simulation.terminated
    ? "Tamamlandı"
    : simulation.truncated
      ? "Karar sınırına ulaşıldı"
      : "Deney henüz tamamlanmadı";

  const averageWaiting =
    simulation.average_waiting_completed === null
      ? "—"
      : `${simulation.average_waiting_completed.toLocaleString("tr-TR", {
          maximumFractionDigits: 2,
        })} adım`;

  const cards = [
    {
      title: "Simülasyon zamanı",
      value: `${simulation.current_step} adım`,
      badge: simulation.algorithm,
      detail: `${simulation.decision_count} karar uygulandı`,
      description: "Atama kararı zamanı ilerletmez.",
    },
    {
      title: "Bekleyen görevler",
      value: String(simulation.queue_count),
      badge: `${simulation.running_count} çalışıyor`,
      detail: `${simulation.pending_count} görev henüz gelmedi`,
      description: "Görevler geliş sırasıyla işlenir.",
    },
    {
      title: "Tamamlanan görevler",
      value: `${simulation.completed_count} / ${simulation.total_jobs}`,
      badge: `%${completionRate.toFixed(0)}`,
      detail: episodeStatus,
      description: "Tamamlanan görevler kaynaklarını bırakır.",
    },
    {
      title: "Ortalama bekleme",
      value: averageWaiting,
      badge: "Tamamlanan işler",
      detail: `Toplam ödül: ${simulation.total_reward.toLocaleString("tr-TR")}`,
      description: "Yalnızca tamamlanan görevlerin ortalaması.",
    },
  ];

  return (
    <div className="scheduler-metrics grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      {cards.map((card, index) => (
        <Card
          key={card.title}
          className={`@container/card overflow-hidden border border-t-2 border-[#333943] bg-[#191c22] text-slate-100 shadow-sm ${
            index === 0
              ? "border-t-orange-500"
              : "border-t-[#46546b]"
          }`}
        >
          <CardHeader>
            <CardDescription className="text-slate-400">
              {card.title}
            </CardDescription>

            <CardTitle
              className={`text-2xl font-semibold tabular-nums @[250px]/card:text-3xl ${
                index === 0 ? "text-orange-400" : "text-slate-100"
              }`}
            >
              {card.value}
            </CardTitle>

            <CardAction>
              <Badge
                variant="outline"
                className={
                  index === 0
                    ? "border-orange-500/30 bg-orange-500/10 text-orange-300"
                    : "border-[#35445d] bg-[#202c40] text-slate-300"
                }
              >
                {card.badge}
              </Badge>
            </CardAction>
          </CardHeader>

          <CardFooter className="flex-col items-start gap-1.5 border-t border-[#333943] bg-[#15181e] pt-4 text-sm">
            <div className="font-medium text-slate-200">
              {card.detail}
            </div>

            <div className="text-slate-400">
              {card.description}
            </div>
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}