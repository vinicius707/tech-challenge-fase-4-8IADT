"use client";

import { use } from "react";

import { AuthGate } from "@/components/auth/auth-gate";
import { NewCaseForm } from "@/components/cases/new-case-form";
import { AppShell } from "@/components/shell/app-shell";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default function NovoCasoPage({ params }: PageProps) {
  const { id } = use(params);

  return (
    <AuthGate mode="app">
      <AppShell>
        <NewCaseForm patientId={id} />
      </AppShell>
    </AuthGate>
  );
}
