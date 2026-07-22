"use client";

import { AuthGate } from "@/components/auth/auth-gate";
import { LogoutButton } from "@/components/auth/logout-button";
import { useSessionStore } from "@/lib/auth/session";

function HomeContent() {
  const username = useSessionStore((s) => s.username);
  const role = useSessionStore((s) => s.role);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Limen</h1>
      <p className="text-muted-foreground max-w-md text-center text-sm">
        Protótipo acadêmico — não é um dispositivo médico.
      </p>
      <p className="text-sm">
        Autenticado como{" "}
        <span className="font-medium text-foreground">{username}</span>
        {role ? (
          <>
            {" "}
            (<span className="text-muted-foreground">{role}</span>)
          </>
        ) : null}
      </p>
      <LogoutButton />
    </main>
  );
}

export default function HomePage() {
  return (
    <AuthGate mode="app">
      <HomeContent />
    </AuthGate>
  );
}
