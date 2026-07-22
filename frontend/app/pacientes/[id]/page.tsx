"use client";

import { use } from "react";

import { AuthGate } from "@/components/auth/auth-gate";
import { PatientDetail } from "@/components/patients/patient-detail";
import { AppShell } from "@/components/shell/app-shell";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default function PacienteDetailPage({ params }: PageProps) {
  const { id } = use(params);

  return (
    <AuthGate mode="app">
      <AppShell>
        <PatientDetail patientId={id} />
      </AppShell>
    </AuthGate>
  );
}
