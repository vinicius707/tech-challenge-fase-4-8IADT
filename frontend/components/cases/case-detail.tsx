"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ModalityUploadForm } from "@/components/cases/modality-upload-form";
import { LazyModalityScoresChart } from "@/components/charts/lazy";
import { buttonVariants } from "@/components/ui/button";
import {
  CASE_POLL_INTERVAL_MS,
  CASE_POLL_TIMEOUT_MS,
  fetchCase,
  shouldPollCase,
  type AttachableModality,
} from "@/lib/cases/api";
import { buildModalityScorePoints } from "@/lib/charts/series";
import { cn } from "@/lib/utils";

type CaseDetailViewProps = {
  caseId: string;
};

const ATTACHABLE_MODALITIES: AttachableModality[] = [
  "video",
  "audio",
  "prescriptions",
];

function CaseSkeleton() {
  return (
    <div
      className="flex max-w-xl flex-col gap-4"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
      <div className="h-4 w-full animate-pulse rounded-md bg-muted" />
      <div className="h-4 w-3/4 animate-pulse rounded-md bg-muted" />
      <div className="h-24 w-full animate-pulse rounded-md bg-muted" />
      <p className="text-sm text-muted-foreground">Processando Caso…</p>
    </div>
  );
}

export function CaseDetailView({ caseId }: CaseDetailViewProps) {
  const queryClient = useQueryClient();
  const [pollTimedOut, setPollTimedOut] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(
      () => setPollTimedOut(true),
      CASE_POLL_TIMEOUT_MS,
    );
    return () => window.clearTimeout(timer);
  }, []);

  const caseQuery = useQuery({
    queryKey: ["cases", caseId],
    queryFn: () => fetchCase(caseId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || !shouldPollCase(data.status) || pollTimedOut) {
        return false;
      }
      return CASE_POLL_INTERVAL_MS;
    },
  });

  if (caseQuery.isLoading) {
    return <CaseSkeleton />;
  }

  if (caseQuery.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {(caseQuery.error as Error).message}
      </p>
    );
  }

  const detail = caseQuery.data;
  if (!detail) return null;

  const polling = shouldPollCase(detail.status);
  const showProcessing = polling && !pollTimedOut;
  const vitals = detail.modalities.find((m) => m.modality === "vitals");
  const present = new Set(detail.modalities.map((m) => m.modality));
  const missingUploads = ATTACHABLE_MODALITIES.filter((m) => !present.has(m));

  if (showProcessing) {
    return (
      <div className="flex max-w-xl flex-col gap-4">
        <header className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Caso</h1>
          <p className="font-mono text-xs text-muted-foreground">{detail.id}</p>
        </header>
        <dl className="grid gap-2 text-sm">
          <div>
            <dt className="text-muted-foreground">Status</dt>
            <dd className="font-medium">{detail.status}</dd>
          </div>
          {vitals ? (
            <div>
              <dt className="text-muted-foreground">Modalidade vitals</dt>
              <dd className="font-medium">{vitals.status}</dd>
            </div>
          ) : null}
        </dl>
        <CaseSkeleton />
      </div>
    );
  }

  return (
    <div className="flex max-w-xl flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Caso</h1>
        <p className="font-mono text-xs text-muted-foreground">{detail.id}</p>
      </header>

      <dl className="grid gap-3 text-sm">
        <div>
          <dt className="text-muted-foreground">Status</dt>
          <dd className="font-medium">{detail.status}</dd>
        </div>
        {vitals ? (
          <div>
            <dt className="text-muted-foreground">Modalidade vitals</dt>
            <dd className="font-medium">{vitals.status}</dd>
          </div>
        ) : null}
        {detail.status === "done" ? (
          <>
            <div>
              <dt className="text-muted-foreground">Risco (score)</dt>
              <dd className="font-medium">
                {detail.riskScore === null ? "—" : detail.riskScore.toFixed(2)}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Nível de Risco</dt>
              <dd className="font-medium">{detail.riskLevel ?? "—"}</dd>
            </div>
          </>
        ) : null}
      </dl>

      {polling && pollTimedOut ? (
        <p role="status" className="text-sm text-muted-foreground">
          Processamento ainda em andamento após{" "}
          {Math.round(CASE_POLL_TIMEOUT_MS / 1000)}s. A atualização automática
          foi pausada (timeout de UX); recarregue a página para tentar de novo.
        </p>
      ) : null}

      {missingUploads.length > 0 ? (
        <section
          aria-labelledby="modality-uploads-heading"
          className="flex flex-col gap-3"
        >
          <h2 id="modality-uploads-heading" className="text-sm font-medium">
            Anexar modalidades
          </h2>
          <p className="text-xs text-muted-foreground">
            Envie video, áudio ou prescriptions com rótulos e erros associados
            ao controle (teclado: Tab / Enter).
          </p>
          {missingUploads.map((modality) => (
            <ModalityUploadForm
              key={modality}
              caseId={caseId}
              modality={modality}
              onAttached={(updated) => {
                queryClient.setQueryData(["cases", caseId], updated);
              }}
            />
          ))}
        </section>
      ) : null}

      {detail.status === "done" && detail.justification ? (
        <section
          aria-labelledby="justification-heading"
          className="flex flex-col gap-2"
        >
          <h2 id="justification-heading" className="text-sm font-medium">
            Justificativa
          </h2>
          <p className="text-sm">{detail.justification.narrative}</p>
          <ul className="list-inside list-disc text-sm text-muted-foreground">
            {detail.justification.modalities.map((entry) => (
              <li key={entry.modality}>
                {entry.status === "done" ? (
                  <>
                    {entry.modality}: {entry.partialLevel ?? "—"} (
                    {entry.partialScore === null
                      ? "—"
                      : entry.partialScore.toFixed(2)}
                    )
                    {entry.topAnomalies.length > 0
                      ? ` — ${entry.topAnomalies.join(", ")}`
                      : ""}
                  </>
                ) : (
                  <>
                    {entry.modality}: indisponível ({entry.status})
                  </>
                )}
              </li>
            ))}
          </ul>
          <div className="pt-2">
            <h3 className="mb-2 text-sm font-medium">
              Scores parciais por modalidade
            </h3>
            <LazyModalityScoresChart
              points={buildModalityScorePoints(detail.justification.modalities)}
            />
          </div>
        </section>
      ) : null}

      {detail.status === "done" ? (
        <section aria-labelledby="alerts-heading" className="flex flex-col gap-2">
          <h2 id="alerts-heading" className="text-sm font-medium">
            Alertas
          </h2>
          {detail.alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum Alerta.</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {detail.alerts.map((alert) => (
                <li key={alert.id}>
                  <a
                    href={`#alerta-${alert.id}`}
                    id={`alerta-${alert.id}`}
                    className="block rounded-md px-2 py-1.5 text-sm outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50"
                  >
                    {alert.level} (v{alert.version})
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {detail.status === "failed" ? (
        <p role="alert" className="text-sm text-destructive">
          O processamento do Caso falhou.
        </p>
      ) : null}

      <Link
        href={`/pacientes/${detail.patientId}`}
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "w-fit")}
      >
        Voltar ao Paciente
      </Link>
    </div>
  );
}
