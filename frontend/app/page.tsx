"use client";

import { AuthGate } from "@/components/auth/auth-gate";
import { AppShell } from "@/components/shell/app-shell";

function HomeContent() {
  return (
    <div className="flex max-w-xl flex-col gap-3">
      <h1 className="text-2xl font-semibold tracking-tight">Início</h1>
      <p className="text-sm text-muted-foreground">
        Protótipo acadêmico — não é um dispositivo médico. Use a navegação para
        abrir Pacientes (fluxo do Épico 4).
      </p>
    </div>
  );
}

export default function HomePage() {
  return (
    <AuthGate mode="app">
      <AppShell>
        <HomeContent />
      </AppShell>
    </AuthGate>
  );
}
