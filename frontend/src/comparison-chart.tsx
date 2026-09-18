interface ComparisonChartRow {
  algorithm: string;
  finished: boolean;
  average_waiting: number | null;
}

interface ComparisonChartProps {
  results: ComparisonChartRow[];
}

const numberFormatter = new Intl.NumberFormat("tr-TR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function getBarColor(algorithm: string): string {
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

  const largestValue = Math.max(...values);
  const axisMaximum = largestValue > 0 ? largestValue * 1.15 : 1;
  const lowestValue = Math.min(...values);
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <figure
      aria-label="Algoritmalara göre ortalama görev bekleme süresi"
      className="min-w-0 rounded-xl border border-slate-700/70 bg-[#111820] p-4 sm:p-6"
    >
      <figcaption className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-100">
            Ortalama bekleme süresi
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Aynı görevler, beş yöntem. Daha kısa çubuk daha iyi.
          </p>
        </div>

        <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-xs font-medium text-orange-400">
          En düşük: {numberFormatter.format(lowestValue)} adım
        </span>
      </figcaption>

      <div className="space-y-5">
        {rows.map((row) => {
          const width =
            row.value === null ? 0 : (row.value / axisMaximum) * 100;

          return (
            <div
              key={row.algorithm}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 sm:grid-cols-[120px_minmax(0,1fr)_90px]"
            >
              <span className="text-sm font-medium text-slate-200">
                {row.algorithm}
              </span>

              <div
                aria-hidden="true"
                className="relative col-span-2 col-start-1 row-start-2 h-8 overflow-hidden rounded-md bg-slate-800/60 sm:col-span-1 sm:col-start-2 sm:row-start-1"
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
                      width: `${width}%`,
                      backgroundColor: getBarColor(row.algorithm),
                    }}
                  />
                )}
              </div>

              <span className="col-start-2 row-start-1 text-right text-sm tabular-nums text-slate-100 sm:col-start-3">
                {row.value === null
                  ? "—"
                  : numberFormatter.format(row.value)}
              </span>
            </div>
          );
        })}
      </div>

      <div
        aria-hidden="true"
        className="mt-4 sm:pl-[136px] sm:pr-[106px]"
      >
        <div className="flex justify-between border-t border-slate-700 pt-2 text-[11px] tabular-nums text-slate-500">
          {ticks.map((tick) => (
            <span key={tick}>
              {numberFormatter.format(axisMaximum * tick)}
            </span>
          ))}
        </div>
        <p className="mt-2 text-center text-xs text-slate-500">
          Ortalama bekleme (adım)
        </p>
      </div>

      <p className="mt-5 border-t border-slate-700/60 pt-4 text-xs leading-5 text-slate-400">
        Her çubuk, bu karşılaştırmadaki tamamlanmış deneyin sonucudur.
        Tamamlanmayan deneyler çizilmez. Sıfır bekleme, sıfır uzunlukta
        çubuk olarak gösterilir.
      </p>
    </figure>
  );
}