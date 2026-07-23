"use client";

import Link from "next/link";

import {
  ALERTS_REGION_HEADING_ID,
  ALERTS_REGION_ID,
  useAlertsFeedStore,
} from "@/lib/alerts/feed";

function eventLabel(event: string): string {
  if (event === "alert.updated") return "Atualizado";
  if (event === "alert.created") return "Novo";
  return event;
}

/**
 * Região de Alertas navegável por teclado (landmark + heading + lista com links).
 */
export function AlertsFeedRegion() {
  const items = useAlertsFeedStore((s) => s.items);
  const connected = useAlertsFeedStore((s) => s.connected);

  return (
    <section
      id={ALERTS_REGION_ID}
      aria-labelledby={ALERTS_REGION_HEADING_ID}
      className="flex max-w-xl flex-col gap-4"
    >
      <header className="flex flex-col gap-1">
        <h1
          id={ALERTS_REGION_HEADING_ID}
          className="text-2xl font-semibold tracking-tight"
        >
          Alertas
        </h1>
        <p className="text-sm text-muted-foreground">
          {connected
            ? "Feed ao vivo via SSE. Use Tab para percorrer a lista."
            : "Aguardando conexão com o feed SSE…"}
        </p>
      </header>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhum Alerta recebido nesta sessão. Quando um Caso gerar Risco ≥
          MEDIO, o evento aparece aqui e um toast polite anuncia.
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {items.map((item) => (
            <li key={item.key}>
              <Link
                href={`/casos/${item.data.caseId}`}
                className="block rounded-md border border-border px-3 py-2 text-sm transition-colors hover:bg-muted/60 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                <span className="font-medium text-foreground">
                  {eventLabel(item.event)} · {item.data.level} (v
                  {item.data.version})
                </span>
                <span className="mt-0.5 block font-mono text-xs text-muted-foreground">
                  Caso {item.data.caseId}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
