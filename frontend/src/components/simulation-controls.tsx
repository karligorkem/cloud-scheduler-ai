import { useCallback, useEffect, useRef, useState } from "react";

import { useSimulation } from "@/components/simulation-provider";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type Algorithm =
  | "First Fit"
  | "Best Fit"
  | "Best Fit RAM"
  | "PPO"
  | "PPO Queue";

interface ActionResult {
  current_step: number;
  decision_count: number;
  terminated: boolean;
  truncated: boolean;
}

function isAlgorithm(value: string): value is Algorithm {
  return (
    value === "First Fit" ||
    value === "Best Fit" ||
    value === "Best Fit RAM" ||
    value === "PPO" ||
    value === "PPO Queue"
  );
}

export function SimulationControls() {
  const { data, error: connectionError, refresh } = useSimulation();

  const [seed, setSeed] = useState("42");
  const [algorithm, setAlgorithm] = useState<Algorithm>("First Fit");

  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [delay, setDelay] = useState(700);

  const [message, setMessage] = useState("");
  const [actionError, setActionError] = useState("");

  const requestInFlight = useRef(false);

  const hasData = data !== null;
  const ended = Boolean(data?.terminated || data?.truncated);

  const activeSeed = data?.seed;
  const activeAlgorithm = data?.algorithm;

  // Sunucudaki deney değiştiğinde formu mevcut deneyle eşleştir.
  // Her veri yenilenmesinde kullanıcının seçimini ezme.
  useEffect(() => {
    if (activeSeed !== undefined) {
      setSeed(String(activeSeed));
    }

    if (activeAlgorithm && isAlgorithm(activeAlgorithm)) {
      setAlgorithm(activeAlgorithm);
    }
  }, [activeSeed, activeAlgorithm]);

  const sendAction = useCallback(
    async (
      action: "reset" | "step",
      nextSeed?: number,
      nextAlgorithm?: Algorithm,
    ) => {
      if (requestInFlight.current) return;

      requestInFlight.current = true;
      setBusy(true);
      setActionError("");
      setMessage("");

      const controller = new AbortController();

      const timeout = window.setTimeout(() => {
        controller.abort();
      }, 15000);

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/api/${action}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body:
              action === "reset"
                ? JSON.stringify({
                    seed: nextSeed,
                    algorithm: nextAlgorithm,
                  })
                : undefined,
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          if (response.status === 409) {
            throw new Error(
              "Deney sona ermiş. Yeni deneyi başlat düğmesini kullan.",
            );
          }

          const body = await response.json().catch(() => null);

          throw new Error(
            typeof body?.detail === "string"
              ? body.detail
              : `İşlem başarısız oldu (${response.status}).`,
          );
        }

        const result: ActionResult = await response.json();

        if (action === "reset") {
          setMessage(
            `${nextAlgorithm} seçildi. Seed ${nextSeed} ile yeni deney hazır.`,
          );
        } else if (result.terminated) {
          setRunning(false);
          setMessage("Bütün görevler tamamlandı. Oynatma durduruldu.");
        } else if (result.truncated) {
          setRunning(false);
          setMessage("Karar sınırına ulaşıldı. Oynatma durduruldu.");
        } else {
          setMessage(
            `Karar ${result.decision_count} uygulandı. ` +
            `Simülasyon zamanı: ${result.current_step}.`,
          );
        }
      } catch (cause) {
        setRunning(false);

        const uncertainResult =
          controller.signal.aborted || cause instanceof TypeError;

        setActionError(
          uncertainResult
            ? "Bağlantı kesildi veya istek zaman aşımına uğradı. " +
              "İşlem uygulanmış olabilir; devam etmeden önce durumu yenile."
            : cause instanceof Error
              ? cause.message
              : "Beklenmeyen bir hata oluştu.",
        );
      } finally {
        window.clearTimeout(timeout);

        await refresh();

        requestInFlight.current = false;
        setBusy(false);
      }
    },
    [refresh],
  );

  useEffect(() => {
    if (connectionError || ended) {
      setRunning(false);
    }
  }, [connectionError, ended]);

  // Veri nesnesindeki her değişiklik zamanlayıcıyı yeniden başlatmaz.
  useEffect(() => {
    if (
      !running ||
      !hasData ||
      ended ||
      connectionError ||
      actionError
    ) {
      return;
    }

    const interval = window.setInterval(() => {
      if (requestInFlight.current) return;

      void sendAction("step");
    }, delay);

    return () => {
      window.clearInterval(interval);
    };
  }, [
    running,
    hasData,
    ended,
    connectionError,
    actionError,
    delay,
    sendAction,
  ]);

  function createEpisode() {
    const numericSeed = Number(seed);

    if (
      seed.trim() === "" ||
      !Number.isInteger(numericSeed) ||
      numericSeed < 0 ||
      numericSeed > 2147483647
    ) {
      setMessage("");
      setActionError(
        "Seed, 0 ile 2147483647 arasında bir tam sayı olmalı.",
      );
      return;
    }

    setRunning(false);
    void sendAction("reset", numericSeed, algorithm);
  }

  async function refreshState() {
    setRunning(false);
    setActionError("");
    setMessage("");
    await refresh();
  }

  // Formda değişiklik varsa mevcut deneyi yanlış yöntemle oynatma.
  const settingsChanged =
    hasData &&
    (
      algorithm !== data.algorithm ||
      seed.trim() === "" ||
      Number(seed) !== data.seed
    );

  const cannotAdvance =
    !hasData ||
    ended ||
    busy ||
    Boolean(connectionError) ||
    Boolean(actionError) ||
    settingsChanged;

  const status = connectionError
    ? "Bağlantı sorunu"
    : !data
      ? "Bağlanıyor"
      : data.terminated
        ? "Tamamlandı"
        : data.truncated
          ? "Karar sınırına ulaşıldı"
          : running
            ? "Otomatik oynatılıyor"
            : "Duraklatıldı";

  const fieldClass =
    "h-9 rounded-md border border-input bg-background px-3 text-sm " +
    "outline-none focus-visible:ring-2 focus-visible:ring-ring " +
    "disabled:opacity-50";

  return (
    <div className="px-4 lg:px-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Simülasyon kontrolü</CardTitle>

              <CardDescription className="mt-2">
                Aktif yöntem: {data?.algorithm ?? "—"}
                {" · "}
                Aktif seed: {data?.seed ?? "—"}
              </CardDescription>
            </div>

            <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-xs text-orange-300">
              {status}
            </span>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-2">
              <label
                htmlFor="simulation-algorithm"
                className="block text-sm font-medium"
              >
                Zamanlama algoritması
              </label>

              <select
                id="simulation-algorithm"
                value={algorithm}
                disabled={busy || running}
                onChange={(event) => {
                  const value = event.target.value;

                  if (isAlgorithm(value)) {
                    setAlgorithm(value);
                  }
                }}
                className={`${fieldClass} min-w-40`}
              >
                <option value="First Fit">First Fit</option>
                <option value="Best Fit">Best Fit</option>
                <option value="Best Fit RAM">Best Fit RAM</option>
                <option value="PPO">PPO — 14 girdi</option>
                <option value="PPO Queue">PPO Queue — 26 girdi</option>
              </select>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="simulation-seed"
                className="block text-sm font-medium"
              >
                Deney seed’i
              </label>

              <input
                id="simulation-seed"
                type="number"
                min={0}
                max={2147483647}
                step={1}
                value={seed}
                disabled={busy || running}
                onChange={(event) => setSeed(event.target.value)}
                className={`${fieldClass} w-32`}
              />
            </div>

            <Button
              type="button"
              variant="outline"
              disabled={busy || running}
              onClick={createEpisode}
            >
              Yeni deneyi başlat
            </Button>

            <div className="space-y-2">
              <label
                htmlFor="simulation-speed"
                className="block text-sm font-medium"
              >
                Oynatma hızı
              </label>

              <select
                id="simulation-speed"
                value={delay}
                onChange={(event) => setDelay(Number(event.target.value))}
                className={fieldClass}
              >
                <option value={1500}>Yavaş</option>
                <option value={700}>Normal</option>
                <option value={200}>Hızlı</option>
              </select>
            </div>

            <Button
              type="button"
              disabled={!running && cannotAdvance}
              onClick={() => {
                if (running) {
                  setRunning(false);
                } else {
                  setMessage("");
                  setRunning(true);
                }
              }}
            >
              {running ? "Duraklat" : "Oynat"}
            </Button>

            <Button
              type="button"
              variant="outline"
              disabled={running || cannotAdvance}
              onClick={() => void sendAction("step")}
            >
              Tek karar
            </Button>

            <Button
              type="button"
              variant="outline"
              disabled={busy || running}
              onClick={() => void refreshState()}
            >
              Durumu yenile
            </Button>
          </div>

          <p className="text-xs leading-5 text-muted-foreground">
            Yeni deneyi başlat mevcut deneyi sıfırlar ve seçilen
            algoritmayı uygular. Oynat, hazır deneyi ilerletir.
            Aynı seed aynı görevleri üretir.
          </p>

          {settingsChanged && (
            <p className="rounded-md border border-orange-500/30 bg-orange-500/10 px-3 py-2 text-sm text-orange-200">
              Yeni ayarlar henüz uygulanmadı. Yeni deneyi başlat
              düğmesine bas.
            </p>
          )}

          {busy && (
            <p className="text-xs text-muted-foreground">
              İşlem uygulanıyor…
            </p>
          )}

          {message && (
            <p
              role="status"
              className="rounded-md border border-slate-600/40 bg-[#202c40] px-3 py-2 text-sm text-slate-200"
            >
              {message}
            </p>
          )}

          {actionError && (
            <p
              role="alert"
              className="rounded-md border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-sm text-orange-200"
            >
              {actionError}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}