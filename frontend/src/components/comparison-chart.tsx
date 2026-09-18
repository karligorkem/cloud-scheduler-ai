interface ComparisonChartRow {
  algorithm: string;
  finished: boolean;
  average_waiting: number | null;
}

interface ComparisonChartProps {
  results: ComparisonChartRow[];
}

const formatter = new Intl.NumberFormat("tr-TR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function barColor(algorithm: string): string {
  if (algorithm === "PPO Queue") return "#fb923c";
  if (algorithm === "PPO") return "#f97316";
  if (algorithm === "Best Fit RAM") return "#94a3b8";
  if (algorithm === "Best Fit") return "#64748b";
  return "#415a80";
}

export function ComparisonChart({ results }: ComparisonChartProps) {
  const rows = results.map((result) => ({
    algorithm: result.algorithm,
    value:
      result.finished &&
      result.average_waiting !== null &&
      Number.isFinite(result.average_waiting) &&
      result.average_waiting >= 0
        ? result.average_waiting
        : null,
  }));

  const values = rows.flatMap((row) =>
    row.value === null ? [] : [row.value],
  );

  if (values.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-700 p-6 text-sm text-slate-400">
        Grafik için tamamlanmış bir deney sonucu gerekiyor.
      </div>
    );
  }

  const maximum = Math.max(...values);
  const axisMaximum = maximum > 0 ? maximum * 1.15 : 1;
  const minimum = Math.min(...values);

  return (
    <figure
      aria-label="Algoritmalara göre ortalama bekleme süresi"
      className="min-w-0 rounded-xl border border-slate-700/70 bg-[#111820] p-4 sm:p-6"
    >
      <figcaption className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-100">
            Ortalama bekleme süresi
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Daha kısa çubuk, daha az bekleme.
          </p>
        </div>

        <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-xs text-orange-400">
          En düşük: {formatter.format(minimum)} adım
        </span>
      </figcaption>

      <div className="space-y-5">
        {rows.map((row) => (
          <div key={row.algorithm}>
            <div className="mb-2 flex items-center justify-between gap-4 text-sm">
              <span className="font-medium text-slate-200">
                {row.algorithm}
              </span>

              <span className="tabular-nums text-slate-100">
                {row.value === null
                  ? "Tamamlanmadı"
                  : `${formatter.format(row.value)} adım`}
              </span>
            </div>

            <div
              aria-hidden="true"
              className="relative h-8 overflow-hidden rounded-md bg-slate-800/60"
            >
              {[25, 50, 75].map((position) => (
                <span
                  key={position}
                  className="absolute inset-y-0 border-l border-slate-600/30"
                  style={{ left: `${position}%` }}
                />
              ))}

              {row.value !== null && (
                <div
                  className="relative h-full rounded-r-md"
                  style={{
                    width: `${(row.value / axisMaximum) * 100}%`,
                    backgroundColor: barColor(row.algorithm),
                  }}
                />
              )}
            </div>
          </div>
        ))}
      </div>

      <div
        aria-hidden="true"
        className="mt-4 flex justify-between border-t border-slate-700 pt-2 text-xs tabular-nums text-slate-500"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
          <span key={tick}>
            {formatter.format(axisMaximum * tick)}
          </span>
        ))}
      </div>

      <p className="mt-2 text-center text-xs text-slate-500">
        Ortalama bekleme (adım)
      </p>

      <p className="mt-5 border-t border-slate-700/60 pt-4 text-xs leading-5 text-slate-400">
        Grafik bu karşılaştırmanın gerçek sonuçlarını gösterir.
        Tamamlanmayan deneyler çizilmez. Sıfır beklemede çubuk uzunluğu
        sıfırdır.
      </p>
    </figure>
  );
}