"use client";

import { AuthGate } from "@/components/auth/auth-gate";
import { AppShell } from "@/components/shell/app-shell";

/**
 * Placeholder mínimo para o item de nav Pacientes (listagem real: T4.4).
 */
export default function PacientesPlaceholderPage() {
  return (
    <AuthGate mode="app">
      <AppShell>
        <div className="flex max-w-xl flex-col gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Pacientes</h1>
          <p className="text-sm text-muted-foreground">
            A listagem e o detalhe entram na próxima tarefa do Épico 4.
          </p>
        </div>
      </AppShell>
    </AuthGate>
  );
}
