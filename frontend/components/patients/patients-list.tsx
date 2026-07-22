"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  createPatient,
  fetchPatients,
  formatPatientLabel,
} from "@/lib/patients/api";
import { cn } from "@/lib/utils";

export function PatientsList() {
  const queryClient = useQueryClient();
  const patientsQuery = useQuery({
    queryKey: ["patients"],
    queryFn: fetchPatients,
  });

  const createMutation = useMutation({
    mutationFn: createPatient,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Pacientes</h1>
        <Button
          type="button"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
        >
          {createMutation.isPending ? "Criando…" : "Novo Paciente"}
        </Button>
      </div>

      {patientsQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando Pacientes…</p>
      ) : null}

      {patientsQuery.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {(patientsQuery.error as Error).message}
        </p>
      ) : null}

      {createMutation.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {(createMutation.error as Error).message}
        </p>
      ) : null}

      {patientsQuery.data ? (
        patientsQuery.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhum Paciente cadastrado. Crie o primeiro para começar.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Rótulo</TableHead>
                <TableHead className="text-right">Ação</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {patientsQuery.data.map((patient) => (
                <TableRow key={patient.id}>
                  <TableCell className="font-medium">{patient.code}</TableCell>
                  <TableCell>{formatPatientLabel(patient)}</TableCell>
                  <TableCell className="text-right">
                    <Link
                      href={`/pacientes/${patient.id}`}
                      className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                    >
                      Abrir
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )
      ) : null}
    </div>
  );
}
