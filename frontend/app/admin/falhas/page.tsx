"use client";

import { AdminGate } from "@/components/admin/admin-gate";
import { FailuresAdminPanel } from "@/components/admin/failures-admin-panel";
import { AuthGate } from "@/components/auth/auth-gate";
import { AppShell } from "@/components/shell/app-shell";

export default function AdminFalhasPage() {
  return (
    <AuthGate mode="app">
      <AppShell>
        <AdminGate>
          <FailuresAdminPanel />
        </AdminGate>
      </AppShell>
    </AuthGate>
  );
}
