import { useRef, useState } from "react";

import { ComparisonChart } from "@/components/comparison-chart";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ComparisonRow {
  algorithm: string;
  workload_seed: number;
  completed_count: number;
  job_count: number;
  finished: boolean;
  truncated: boolean;
  elapsed_steps: number;
  decision_count: number;
  total_reward: number;
  average_waiting: number | null;
  improvement_percent: number | null;
}

interface ComparisonResult {
  seed: number;
  workload_seed: number;
  results: ComparisonRow[];
}

const formatter = new Intl.NumberFormat("tr-TR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return formatter.format(value);
}

function formatImprovement(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";

  const rounded = Math.abs(value) < 0.005 ? 0 : value;
  return `%${formatter.format(rounded)}`;
}

export function AlgorithmComparison() {
  const [seed, setSeed] = useState("42");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ComparisonResult | null>(null);

  const requestInFlight = useRef(false);

  async function compareAlgorithms(): Promise<void> {
    if (requestInFlight.current) return;

    const parsedSeed = Number(seed);

    if (
      seed.trim() === "" ||
      !Number.isInteger(parsedSeed) ||
      parsedSeed < 0 ||
      parsedSeed > 2 ** 31 - 1
    ) {
      setError("Seed, 0 ile 2147483647 arasında bir tam sayı olmalı.");
      return;
    }

    requestInFlight.current = true;
    setBusy(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/compare", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ seed: parsedSeed }),
      });

      if (!response.ok) {
        let message = `Karşılaştırma başarısız. HTTP ${response.status}`;

        const body: unknown = await response.json().catch(() => null);

        if (
          typeof body === "object" &&
          body !== null &&
          "detail" in body &&
          typeof body.detail === "string"
        ) {
          message = body.detail;
        }

        throw new Error(message);
      }

      const comparison: ComparisonResult = await response.json();
      setResult(comparison);
    } catch (caughtError) {
      if (caughtError instanceof TypeError) {
        setError(
          "Backend'e bağlanılamadı. 8000 portunda çalıştığını kontrol et.",
        );
      } else {
        setError(
          caughtError instanceof Error
            ? caughtError.message
            : "Karşılaştırma sırasında bir hata oluştu.",
        );
      }
    } finally {
      requestInFlight.current = false;
      setBusy(false);
    }
  }

  return (
    <section
      id="comparison"
      aria-labelledby="comparison-title"
      className="min-w-0 scroll-mt-20 px-4 lg:px-6"
    >
      <Card className="min-w-0 border-slate-700/70 bg-[#191c22]">
        <CardHeader>
          <CardTitle id="comparison-title" className="text-slate-100">
            Algoritma karşılaştırması
          </CardTitle>
          <CardDescription className="text-slate-400">
            Beş yöntem, aynı görevler. Daha düşük bekleme daha iyi.
          </CardDescription>
        </CardHeader>

        <CardContent className="min-w-0 space-y-6">
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              void compareAlgorithms();
            }}
          >
            <div className="space-y-2">
              <label
                htmlFor="comparison-seed"
                className="block text-sm font-medium text-slate-200"
              >
                Karşılaştırma seed’i
              </label>

              <input
                id="comparison-seed"
                type="number"
                min={0}
                max={2147483647}
                step={1}
                required
                value={seed}
                disabled={busy}
                onChange={(event) => setSeed(event.target.value)}
                className="h-10 w-40 rounded-lg border border-slate-600 bg-[#0d0f12] px-3 text-sm text-slate-100 outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 disabled:opacity-50"
              />
            </div>

            <Button
              type="submit"
              disabled={busy}
              className="h-10 bg-orange-500 text-black hover:bg-orange-400"
            >
              {busy ? "Karşılaştırılıyor…" : "Beş yöntemi karşılaştır"}
            </Button>
          </form>

          <p className="text-xs leading-5 text-slate-400">
            Her yöntem bağımsız bir simülasyonda çalışır. Mevcut canlı
            deney değişmez. Sonuçlar tek senaryoya aittir; genel başarı
            sıralaması değildir.
          </p>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
            >
              {error}
            </div>
          )}

          {busy && (
            <div
              role="status"
              className="rounded-lg border border-slate-700 bg-slate-800/50 p-4 text-sm text-slate-300"
            >
              Modeller yükleniyor ve beş yöntem aynı görevlerle
              çalıştırılıyor. İlk karşılaştırma biraz sürebilir.
            </div>
          )}

          {!busy && result === null && !error && (
            <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
              Karşılaştırmayı başlattığında grafik ve sonuç tablosu burada
              görünecek.
            </div>
          )}

          {result !== null && (
            <div className="min-w-0 space-y-6">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="rounded-full border border-slate-700 bg-[#111b2c] px-3 py-1.5 text-slate-300">
                  Sonuç seed’i: {result.seed}
                </span>

                <span className="rounded-full border border-slate-700 bg-[#111b2c] px-3 py-1.5 text-slate-300">
                  Görev seed’i: {result.workload_seed}
                </span>

                <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1.5 text-orange-400">
                  Tamamlanan yöntem:{" "}
                  {result.results.filter((row) => row.finished).length}
                  {" / "}
                  {result.results.length}
                </span>
              </div>

              <ComparisonChart results={result.results} />

              <div className="min-w-0 overflow-x-auto rounded-xl border border-slate-700/80">
                <table className="w-full min-w-[850px] text-left text-sm">
                  <caption className="sr-only">
                    Seed {result.seed} için algoritma karşılaştırma
                    sonuçları
                  </caption>

                  <thead className="bg-[#111b2c] text-xs text-slate-300">
                    <tr>
                      <th scope="col" className="px-4 py-3">
                        Yöntem
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Tamamlanan
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Durum
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        Süre
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        Ort. bekleme
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        Toplam ödül
                      </th>
                      <th scope="col" className="px-4 py-3 text-right">
                        First Fit’e göre azalma
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {result.results.map((row) => (
                      <tr
                        key={row.algorithm}
                        className="border-t border-slate-700/70 text-slate-200 even:bg-white/[0.02] hover:bg-white/[0.04]"
                      >
                        <th
                          scope="row"
                          className="whitespace-nowrap px-4 py-4 font-medium text-orange-400"
                        >
                          {row.algorithm}
                        </th>

                        <td className="px-4 py-4 tabular-nums">
                          {row.completed_count} / {row.job_count}
                        </td>

                        <td className="whitespace-nowrap px-4 py-4">
                          <span
                            className={
                              row.finished
                                ? "text-slate-200"
                                : "text-orange-400"
                            }
                          >
                            {row.finished
                              ? "Tamamlandı"
                              : row.truncated
                                ? "Karar sınırında durdu"
                                : "Tamamlanmadı"}
                          </span>
                        </td>

                        <td className="whitespace-nowrap px-4 py-4 text-right tabular-nums">
                          {row.elapsed_steps} adım
                        </td>

                        <td className="px-4 py-4 text-right tabular-nums">
                          {row.finished
                            ? formatNumber(row.average_waiting)
                            : "—"}
                        </td>

                        <td className="px-4 py-4 text-right tabular-nums">
                          {formatNumber(row.total_reward)}
                        </td>

                        <td className="px-4 py-4 text-right tabular-nums">
                          {row.finished
                            ? formatImprovement(row.improvement_percent)
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="text-xs leading-5 text-slate-400">
                Pozitif azalma daha az bekleme, negatif değer daha fazla
                bekleme demektir. Tamamlanmayan deneylerde bekleme
                karşılaştırması yapılmaz.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}