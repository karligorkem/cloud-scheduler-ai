import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface RunningJob {
  id: string;
  remaining_steps: number;
}

interface ServerState {
  id: string;
  is_active: boolean;
  total_cpu: number;
  available_cpu: number;
  total_memory_gb: number;
  available_memory_gb: number;
  total_gpu: number;
  available_gpu: number;
  running_jobs: RunningJob[];
}

interface ServerResponse {
  decision_count: number;
  servers: ServerState[];
}

function ResourceBar({
  label,
  total,
  available,
  unit,
  color,
}: {
  label: string;
  total: number;
  available: number;
  unit: string;
  color: "orange" | "slate";
}) {
  const used = total - available;
  const percentage = total > 0 ? (used / total) * 100 : 0;
  const barWidth = Math.min(100, Math.max(0, percentage));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-slate-300">{label}</span>

        <span className="font-medium tabular-nums text-slate-100">
          {used} / {total} {unit}
        </span>
      </div>

      <div
        role="progressbar"
        aria-label={`${label} ayrılan kaynak oranı`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={barWidth}
        aria-valuetext={`${used} / ${total} ${unit} ayrılmış`}
        className="h-2.5 overflow-hidden rounded-full bg-[#293140]"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none ${
            color === "orange" ? "bg-orange-500" : "bg-slate-400"
          }`}
          style={{ width: `${barWidth}%` }}
        />
      </div>

      <div className="flex justify-between text-xs text-slate-400">
        <span>
          Boş: {available} {unit}
        </span>
        <span>%{percentage.toFixed(0)} ayrılmış</span>
      </div>
    </div>
  );
}

export function ServerCards() {
  const [snapshot, setSnapshot] = useState<ServerResponse | null>(null);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let active = true;

    let controller: AbortController | undefined;
    let pollTimer: ReturnType<typeof setTimeout> | undefined;
    let requestTimer: ReturnType<typeof setTimeout> | undefined;

    async function loadServers() {
      controller = new AbortController();

      requestTimer = setTimeout(() => {
        controller?.abort();
      }, 10000);

      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/state",
          { signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error(`API hata kodu: ${response.status}`);
        }

        const result: ServerResponse = await response.json();

        if (!active) return;

        setSnapshot(result);
        setError("");

        pollTimer = setTimeout(() => {
          void loadServers();
        }, 1500);
      } catch {
        if (!active) return;

        setError("Sunucu verileri alınamadı. API bağlantısını kontrol et.");
      } finally {
        clearTimeout(requestTimer);
      }
    }

    void loadServers();

    return () => {
      active = false;
      controller?.abort();
      clearTimeout(pollTimer);
      clearTimeout(requestTimer);
    };
  }, [retryCount]);

  return (
    <section className="space-y-4 px-4 lg:px-6" id="servers">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Sunucu kümesi</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Görevlere ayrılan CPU, RAM ve GPU kaynakları.
          </p>
        </div>

        {snapshot && !error && (
          <span className="text-xs text-muted-foreground">
            Karar #{snapshot.decision_count} · {snapshot.servers.length} sunucu
          </span>
        )}
      </div>

      {error ? (
        <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-5">
          <p role="alert" className="text-sm text-orange-200">
            {error}
          </p>

          <button
            type="button"
            className="mt-3 rounded-md bg-orange-500 px-4 py-2 text-sm font-medium text-black hover:bg-orange-400"
            onClick={() => {
              setSnapshot(null);
              setError("");
              setRetryCount((count) => count + 1);
            }}
          >
            Tekrar bağlan
          </button>
        </div>
      ) : !snapshot ? (
        <p role="status" className="py-6 text-sm text-muted-foreground">
          Sunucular yükleniyor…
        </p>
      ) : snapshot.servers.length === 0 ? (
        <p className="py-6 text-sm text-muted-foreground">
          Bu deneyde sunucu bulunmuyor.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {snapshot.servers.map((server) => (
            <Card
              key={server.id}
              className="border-[#333943] bg-[#191c22] text-slate-100"
            >
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base">
                    {server.id}
                  </CardTitle>

                  <Badge
                    variant="outline"
                    className="border-[#35445d] bg-[#202c40] text-slate-300"
                  >
                    {server.is_active ? "Aktif" : "Kapalı"}
                  </Badge>
                </div>

                <CardDescription className="text-slate-400">
                  {server.running_jobs.length} görev çalışıyor
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                <ResourceBar
                  label="CPU"
                  total={server.total_cpu}
                  available={server.available_cpu}
                  unit="çekirdek"
                  color="orange"
                />

                <ResourceBar
                  label="RAM"
                  total={server.total_memory_gb}
                  available={server.available_memory_gb}
                  unit="GB"
                  color="slate"
                />

                <div className="flex justify-between border-t border-[#333943] pt-4 text-sm">
                  <span className="text-slate-400">GPU</span>
                  <span>
                    {server.total_gpu === 0
                      ? "GPU bulunmuyor"
                      : `${server.total_gpu - server.available_gpu} / ${server.total_gpu} ayrılmış`}
                  </span>
                </div>

                <div className="space-y-3">
                  <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
                    Çalışan görevler
                  </h3>

                  {server.running_jobs.length === 0 ? (
                    <p className="rounded-lg border border-dashed border-[#35445d] px-4 py-5 text-center text-sm text-slate-400">
                      Sunucu yeni görev bekliyor.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {server.running_jobs.map((job) => (
                        <div
                          key={job.id}
                          className="flex justify-between gap-3 rounded-lg border border-[#30415c] bg-[#152136] px-4 py-3 text-sm"
                        >
                          <span className="font-medium text-orange-300">
                            {job.id}
                          </span>

                          <span className="text-slate-300">
                            {job.remaining_steps} adım kaldı
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}