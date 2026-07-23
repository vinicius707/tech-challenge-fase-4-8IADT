"use client";

import { useAlertsFeedStore } from "@/lib/alerts/feed";
import { useSessionStore } from "@/lib/auth/session";

/**
 * Indicador compacto do feed SSE no header.
 */
export function AlertsStreamIndicator() {
  const accessToken = useSessionStore((s) => s.accessToken);
  const connected = useAlertsFeedStore((s) => s.connected);
  const toast = useAlertsFeedStore((s) => s.toast);

  if (!accessToken) return null;

  const lastEvent = toast?.text ?? null;

  return (
    <p
      className="hidden max-w-[14rem] truncate text-xs text-muted-foreground sm:block"
      title={lastEvent ?? undefined}
      aria-hidden="true"
    >
      {lastEvent
        ? `Alerta: ${lastEvent}`
        : connected
          ? "Alertas: ao vivo"
          : "Alertas: reconectando…"}
    </p>
  );
}
