"use client";

import { useAlertsFeedStore } from "@/lib/alerts/feed";

/**
 * Toast de Alerta com `aria-live="polite"` (E7.2 / T7.7).
 * Anuncia `alert.created` / `alert.updated` sem roubar foco.
 */
export function AlertsToast() {
  const toast = useAlertsFeedStore((s) => s.toast);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="pointer-events-none fixed bottom-4 left-1/2 z-50 w-[min(24rem,calc(100%-2rem))] -translate-x-1/2"
    >
      {toast ? (
        <p
          key={toast.nonce}
          className="rounded-lg border border-border bg-card px-4 py-3 text-sm text-card-foreground shadow-md"
        >
          {toast.text}
        </p>
      ) : null}
    </div>
  );
}
