"use client";

import { useEffect } from "react";

import { useSessionStore } from "@/lib/auth/session";
import { useAlertsFeedStore } from "@/lib/alerts/feed";
import {
  connectAlertsStream,
  nextReconnectDelayMs,
  readAlertSse,
} from "@/lib/alerts/sse";

/**
 * Mantém uma conexão SSE e alimenta o feed/toast (T7.7).
 * Montar uma vez no shell autenticado.
 */
export function AlertsStreamBridge() {
  const accessToken = useSessionStore((s) => s.accessToken);
  const setConnected = useAlertsFeedStore((s) => s.setConnected);
  const pushEvent = useAlertsFeedStore((s) => s.pushEvent);

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
            if (
              message.event === "alert.created" ||
              message.event === "alert.updated"
            ) {
              pushEvent(message);
            }
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
      setConnected(false);
    };
  }, [accessToken, pushEvent, setConnected]);

  return null;
}
