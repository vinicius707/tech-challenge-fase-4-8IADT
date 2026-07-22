"use client";

import { use } from "react";

import { AuthGate } from "@/components/auth/auth-gate";
import { CaseDetailView } from "@/components/cases/case-detail";
import { AppShell } from "@/components/shell/app-shell";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default function CasoDetailPage({ params }: PageProps) {
  const { id } = use(params);

  return (
    <AuthGate mode="app">
      <AppShell>
        <CaseDetailView caseId={id} />
      </AppShell>
    </AuthGate>
  );
}
