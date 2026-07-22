"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createCaseWithVitals,
  createIdempotencyKey,
} from "@/lib/cases/api";
import { cn } from "@/lib/utils";

type NewCaseFormProps = {
  patientId: string;
};

export function NewCaseForm({ patientId }: NewCaseFormProps) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: async (csv: File) => {
      const idempotencyKey = createIdempotencyKey();
      return createCaseWithVitals(patientId, csv, idempotencyKey);
    },
    onSuccess: (created) => {
      router.push(`/casos/${created.id}`);
    },
    onError: (err) => {
      setError((err as Error).message);
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!file) {
      setError("Selecione um arquivo CSV de vitais.");
      return;
    }
    createMutation.mutate(file);
  }

  return (
    <div className="flex max-w-md flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Novo Caso</h1>
        <p className="text-sm text-muted-foreground">
          Envie um CSV de vitais vinculado a este Paciente. Cada envio gera uma
          nova chave de idempotência.
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-2">
          <Label htmlFor="vitals-csv">Arquivo CSV de vitais</Label>
          <Input
            id="vitals-csv"
            name="file"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              const next = event.target.files?.[0] ?? null;
              setFile(next);
              setError(null);
            }}
            required
          />
        </div>

        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Enviando…" : "Criar Caso"}
          </Button>
          <Link
            href={`/pacientes/${patientId}`}
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}
