"use client";

import { useSessionStore } from "@/lib/auth/session";

type AdminGateProps = {
  children: React.ReactNode;
};

/**
 * Bloqueio explícito para não-admin na UI de Falhas (API já retorna 403).
 */
export function AdminGate({ children }: AdminGateProps) {
  const role = useSessionStore((s) => s.role);

  if (role !== "admin") {
    return (
      <div className="flex max-w-lg flex-col gap-2" role="alert">
        <h1 className="text-2xl font-semibold tracking-tight">Acesso negado</h1>
        <p className="text-sm text-muted-foreground">
          Somente Operadores com papel <strong>admin</strong> acessam Falhas de
          Processamento (HTTP 403 na API).
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
