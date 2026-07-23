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
  discardFailure,
  fetchOpenFailures,
  redriveFailure,
  type ProcessingFailure,
} from "@/lib/failures/api";
import { cn } from "@/lib/utils";

function FailureActions({ failure }: { failure: ProcessingFailure }) {
  const queryClient = useQueryClient();

  const redriveMutation = useMutation({
    mutationFn: () => redriveFailure(failure.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin-failures"] });
    },
  });

  const discardMutation = useMutation({
    mutationFn: () => discardFailure(failure.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin-failures"] });
    },
  });

  const pending = redriveMutation.isPending || discardMutation.isPending;
  const actionError =
    (redriveMutation.error as Error | null)?.message ??
    (discardMutation.error as Error | null)?.message ??
    null;

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          size="sm"
          disabled={pending || failure.status !== "open"}
          onClick={() => redriveMutation.mutate()}
        >
          {redriveMutation.isPending ? "Redrive…" : "Redrive"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={pending || failure.status !== "open"}
          onClick={() => discardMutation.mutate()}
        >
          {discardMutation.isPending ? "Descartando…" : "Descartar"}
        </Button>
        <Link
          href={`/casos/${failure.caseId}`}
          className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
        >
          Caso
        </Link>
      </div>
      {actionError ? (
        <p role="alert" className="text-xs text-destructive">
          {actionError}
        </p>
      ) : null}
    </div>
  );
}

export function FailuresAdminPanel() {
  const failuresQuery = useQuery({
    queryKey: ["admin-failures"],
    queryFn: fetchOpenFailures,
  });

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Falhas de Processamento
        </h1>
        <p className="text-sm text-muted-foreground">
          Painel DLQ (admin): listar, inspecionar, redrive ou descartar.
        </p>
      </header>

      {failuresQuery.isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando falhas…</p>
      ) : null}

      {failuresQuery.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {(failuresQuery.error as Error).message}
        </p>
      ) : null}

      {failuresQuery.data ? (
        failuresQuery.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhuma Falha de Processamento aberta.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Modalidade</TableHead>
                <TableHead>Erro</TableHead>
                <TableHead>Tentativas</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {failuresQuery.data.map((failure) => (
                <TableRow key={failure.id}>
                  <TableCell className="font-medium">
                    {failure.modality}
                  </TableCell>
                  <TableCell className="max-w-xs truncate font-mono text-xs">
                    <span title={failure.errorSummary}>
                      {failure.errorSummary}
                    </span>
                  </TableCell>
                  <TableCell>{failure.attempts}</TableCell>
                  <TableCell>{failure.status}</TableCell>
                  <TableCell className="text-right">
                    <FailureActions failure={failure} />
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
