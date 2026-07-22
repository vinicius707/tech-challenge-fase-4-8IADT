"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { buttonVariants } from "@/components/ui/button";
import { fetchPatient, formatPatientLabel } from "@/lib/patients/api";
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

      <dl className="grid gap-3 text-sm">
        <div>
          <dt className="text-muted-foreground">Rótulo Sensível</dt>
          <dd className="font-medium">{formatPatientLabel(patient)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Identificador</dt>
          <dd className="font-mono text-xs">{patient.id}</dd>
        </div>
      </dl>

      <p className="text-sm text-muted-foreground">
        A API desta etapa não expõe listagem de Casos por Paciente; use{" "}
        <strong className="font-medium text-foreground">Novo Caso</strong> para
        criar um Caso de vitais.
      </p>

      <Link
        href="/pacientes"
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "w-fit")}
      >
        Voltar à lista
      </Link>
    </div>
  );
}
