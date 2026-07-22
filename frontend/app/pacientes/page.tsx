"use client";

import { AuthGate } from "@/components/auth/auth-gate";
import { PatientsList } from "@/components/patients/patients-list";
import { AppShell } from "@/components/shell/app-shell";

export default function PacientesPage() {
  return (
    <AuthGate mode="app">
      <AppShell>
        <PatientsList />
      </AppShell>
    </AuthGate>
  );
}
