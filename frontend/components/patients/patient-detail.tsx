"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { LazyRiskTrendChart } from "@/components/charts/lazy";
import { buttonVariants } from "@/components/ui/button";
import { SensitiveLabelReveal } from "@/components/patients/sensitive-label-reveal";
import { buildRiskTrendPoints } from "@/lib/charts/series";
import { fetchPatient } from "@/lib/patients/api";
import { cn } from "@/lib/utils";

type PatientDetailProps = {
  patientId: string;
};

export function PatientDetail({ patientId }: PatientDetailProps) {
  const patientQuery = useQuery({
    queryKey: ["patients", patientId],
    queryFn: () => fetchPatient(patientId),
  });

  if (patientQuery.isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando Paciente…</p>;
  }

  if (patientQuery.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {(patientQuery.error as Error).message}
      </p>
    );
  }

  const patient = patientQuery.data;
  if (!patient) return null;

  // Sem GET de Casos por Paciente ainda — tendência pronta para pontos futuros.
  const trendPoints = buildRiskTrendPoints([]);

  return (
    <div className="flex max-w-xl flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{patient.code}</h1>
        <Link
          href={`/pacientes/${patient.id}/novo-caso`}
          className={cn(buttonVariants())}
        >
          Novo Caso
        </Link>
      </div>

      <SensitiveLabelReveal patient={patient} />

      <dl className="grid gap-3 text-sm">
        <div>
          <dt className="text-muted-foreground">Identificador</dt>
          <dd className="font-mono text-xs">{patient.id}</dd>
        </div>
      </dl>

      <section
        aria-labelledby="risk-trend-heading"
        className="flex flex-col gap-2"
      >
        <h2 id="risk-trend-heading" className="text-sm font-medium">
          Tendência de Risco
        </h2>
        <LazyRiskTrendChart points={trendPoints} />
        <p className="text-xs text-muted-foreground">
          A API ainda não lista Casos por Paciente; o gráfico carrega sob demanda
          (Recharts lazy) e exibirá a série quando o histórico estiver disponível.
        </p>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link
          href="/alertas"
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          Alertas
        </Link>
        <Link
          href="/pacientes"
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          Voltar à lista
        </Link>
      </div>
    </div>
  );
}
