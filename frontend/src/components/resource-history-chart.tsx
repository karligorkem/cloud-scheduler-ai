import { useSimulation } from "@/components/simulation-provider";

const WIDTH = 900;
const HEIGHT = 290;

const LEFT = 52;
const RIGHT = 20;
const TOP = 20;
const BOTTOM = 42;

const PLOT_WIDTH = WIDTH - LEFT - RIGHT;
const PLOT_HEIGHT = HEIGHT - TOP - BOTTOM;

const formatter = new Intl.NumberFormat("tr-TR", {
  maximumFractionDigits: 1,
});

export function ResourceHistoryChart() {
  const { data, error } = useSimulation();

  if (data === null) {
    return (
      <section className="px-4 lg:px-6">
        <div
          role="status"
          className="rounded-xl border border-slate-700 bg-[#191c22] p-6 text-sm text-slate-400"
        >
          {error || "Kaynak geçmişi yükleniyor…"}
        </div>
      </section>
    );
  }

  const history = data.resource_history ?? [];
  const lastPoint = history[history.length - 1];

  const lastStep = lastPoint?.step ?? 0;
  const axisMaximum = Math.max(1, lastStep);

  const x = (step: number) =>
    LEFT + (step / axisMaximum) * PLOT_WIDTH;

  const y = (percent: number) =>
    TOP + (1 - Math.max(0, Math.min(100, percent)) / 100) * PLOT_HEIGHT;

  function makePath(key: "cpu_percent" | "ram_percent"): string {
    return history
      .map((point, index) => {
        if (index === 0) {
          return `M ${x(point.step)} ${y(point[key])}`;
        }

        // Kaynaklar zaman aralığı boyunca sabit kalır.
        // Sonraki zamanda yeni seviyeye geçilir.
        return `H ${x(point.step)} V ${y(point[key])}`;
      })
      .join(" ");
  }

  const tickCount = Math.min(5, axisMaximum);

  const timeTicks = Array.from(
    { length: tickCount + 1 },
    (_, index) => Math.round((index / tickCount) * axisMaximum),
  );

  return (
    <section
      id="resource-history"
      aria-labelledby="resource-history-title"
      className="min-w-0 scroll-mt-20 px-4 lg:px-6"
    >
      <div className="min-w-0 rounded-xl border border-slate-700/70 bg-[#191c22] p-4 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2
              id="resource-history-title"
              className="font-semibold text-slate-100"
            >
              Kaynak kullanımı
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Simülasyon boyunca görevlere ayrılan CPU ve RAM.
            </p>
          </div>

          <span className="rounded-full border border-slate-700 bg-[#111b2c] px-3 py-1 text-xs text-slate-300">
            {data.algorithm} · Seed {data.seed}
          </span>
        </div>

        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <span className="flex items-center gap-2 text-slate-200">
            <span className="h-2.5 w-2.5 rounded-full bg-orange-500" />
            CPU
            <strong className="tabular-nums text-orange-400">
              {lastPoint
                ? `%${formatter.format(lastPoint.cpu_percent)}`
                : "—"}
            </strong>
          </span>

          <span className="flex items-center gap-2 text-slate-200">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-400" />
            RAM
            <strong className="tabular-nums">
              {lastPoint
                ? `%${formatter.format(lastPoint.ram_percent)}`
                : "—"}
            </strong>
          </span>
        </div>

        {error && (
          <p role="status" className="mt-3 text-xs text-orange-400">
            Bağlantı kesildi. Son alınan kaynak geçmişi gösteriliyor.
          </p>
        )}

        {history.length === 0 ? (
          <div className="mt-5 rounded-lg border border-dashed border-slate-700 p-8 text-center text-sm text-slate-400">
            Kaynak geçmişi alınamadı. Backend değişikliklerinin
            kaydedildiğini kontrol et.
          </div>
        ) : (
          <>
            <div className="mt-5 overflow-x-auto rounded-lg bg-[#111820] p-2">
              <svg
                viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
                role="img"
                aria-label={`CPU ve RAM kaynak kullanımı. Son zaman: ${lastStep} adım. CPU yüzde ${formatter.format(lastPoint.cpu_percent)}, RAM yüzde ${formatter.format(lastPoint.ram_percent)}.`}
                className="block w-full min-w-[540px]"
              >
                {[0, 25, 50, 75, 100].map((percent) => (
                  <g key={percent}>
                    <line
                      x1={LEFT}
                      x2={WIDTH - RIGHT}
                      y1={y(percent)}
                      y2={y(percent)}
                      stroke="#334155"
                      strokeOpacity={0.55}
                      strokeDasharray="4 5"
                    />
                    <text
                      x={LEFT - 10}
                      y={y(percent) + 4}
                      textAnchor="end"
                      fill="#94a3b8"
                      fontSize={11}
                    >
                      %{percent}
                    </text>
                  </g>
                ))}

                {timeTicks.map((step) => (
                  <text
                    key={step}
                    x={x(step)}
                    y={HEIGHT - BOTTOM + 22}
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize={11}
                  >
                    {step}
                  </text>
                ))}

                <path
                  d={makePath("cpu_percent")}
                  fill="none"
                  stroke="#f97316"
                  strokeWidth={3}
                  strokeLinejoin="round"
                />

                <path
                  d={makePath("ram_percent")}
                  fill="none"
                  stroke="#94a3b8"
                  strokeWidth={2.5}
                  strokeDasharray="7 5"
                  strokeLinejoin="round"
                />

                <circle
                  cx={x(lastPoint.step)}
                  cy={y(lastPoint.cpu_percent)}
                  r={4}
                  fill="#f97316"
                />

                <circle
                  cx={x(lastPoint.step)}
                  cy={y(lastPoint.ram_percent)}
                  r={4}
                  fill="#94a3b8"
                  stroke="#111820"
                  strokeWidth={1}
                />

                <text
                  x={LEFT + PLOT_WIDTH / 2}
                  y={HEIGHT - 3}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize={11}
                >
                  Simülasyon zamanı (adım)
                </text>
              </svg>
            </div>

            {lastStep === 0 && (
              <p className="mt-3 text-xs text-slate-400">
                İlk zaman noktası gösteriliyor. Simülasyon zamanı
                ilerledikçe çizgiler oluşacak.
              </p>
            )}
          </>
        )}

        <p className="mt-4 border-t border-slate-700/60 pt-4 text-xs leading-5 text-slate-400">
          Turuncu düz çizgi CPU’yu, gri kesikli çizgi RAM’i gösterir.
          Değerler toplam küme kapasitesine göredir. Aynı zamandaki
          atamalar o noktanın değerini günceller. Bunlar simülasyonda
          ayrılan kaynaklardır; bilgisayarının gerçek kullanımı değildir.
        </p>
      </div>
    </section>
  );
}