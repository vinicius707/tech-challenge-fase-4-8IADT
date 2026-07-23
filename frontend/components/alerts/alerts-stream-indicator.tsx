"use client";

import { useEffect, useState } from "react";

import { useSessionStore } from "@/lib/auth/session";
import {
  connectAlertsStream,
  nextReconnectDelayMs,
  readAlertSse,
  type AlertSseMessage,
} from "@/lib/alerts/sse";

function formatSmoke(message: AlertSseMessage): string {
  return `${message.event} · ${message.data.level} v${message.data.version}`;
}

/**
 * Indicador mínimo (smoke) do feed SSE — sem toast/a11y fino (Épico 7.2).
 */
export function AlertsStreamIndicator() {
  const accessToken = useSessionStore((s) => s.accessToken);
  const [lastEvent, setLastEvent] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!accessToken) {
      setConnected(false);
      return;
    }

    const controller = new AbortController();
    let cancelled = false;
    let attempt = 0;

    const sleep = (ms: number) =>
      new Promise<void>((resolve) => {
        window.setTimeout(resolve, ms);
      });

    async function run() {
      while (!cancelled && !controller.signal.aborted) {
        const token = useSessionStore.getState().accessToken;
        if (!token) break;
        try {
          const response = await connectAlertsStream({
            accessToken: token,
            signal: controller.signal,
          });
          if (response.status === 401) {
            setConnected(false);
            break;
          }
          if (!response.ok || !response.body) {
            throw new Error(`SSE HTTP ${response.status}`);
          }
          attempt = 0;
          setConnected(true);
          for await (const message of readAlertSse(response)) {
            if (cancelled) break;
            setLastEvent(formatSmoke(message));
          }
          setConnected(false);
        } catch {
          setConnected(false);
          if (cancelled || controller.signal.aborted) break;
          const delay = nextReconnectDelayMs(attempt);
          attempt += 1;
          await sleep(delay);
        }
      }
    }

    void run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [accessToken]);

  if (!accessToken) return null;

  return (
    <p
      role="status"
      className="hidden max-w-[14rem] truncate text-xs text-muted-foreground sm:block"
      title={lastEvent ?? undefined}
    >
      {lastEvent
        ? `Alerta: ${lastEvent}`
        : connected
          ? "Alertas: ao vivo"
          : "Alertas: reconectando…"}
    </p>
  );
}
