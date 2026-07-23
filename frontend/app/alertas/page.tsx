"use client";

import { AuthGate } from "@/components/auth/auth-gate";
import { AlertsFeedRegion } from "@/components/alerts/alerts-feed";
import { AppShell } from "@/components/shell/app-shell";

export default function AlertasPage() {
  return (
    <AuthGate mode="app">
      <AppShell>
        <AlertsFeedRegion />
      </AppShell>
    </AuthGate>
  );
}
