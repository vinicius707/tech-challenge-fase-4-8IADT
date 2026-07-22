"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import {
  guestBlockedFromApp,
  loggedInBlockedFromLogin,
} from "@/lib/auth/routing";
import { useSessionStore } from "@/lib/auth/session";

type AuthGateProps = {
  children: React.ReactNode;
  /** `app` exige sessão; `login` redireciona se já autenticado. */
  mode: "app" | "login";
};

export function AuthGate({ children, mode }: AuthGateProps) {
  const router = useRouter();
  const hasHydrated = useSessionStore((s) => s.hasHydrated);
  const accessToken = useSessionStore((s) => s.accessToken);
  const isAuthenticated = Boolean(accessToken);

  useEffect(() => {
    if (!hasHydrated) return;
    const target =
      mode === "app"
        ? guestBlockedFromApp(isAuthenticated)
        : loggedInBlockedFromLogin(isAuthenticated);
    if (target) router.replace(target);
  }, [hasHydrated, isAuthenticated, mode, router]);

  if (!hasHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Carregando…
      </div>
    );
  }

  if (mode === "app" && !isAuthenticated) return null;
  if (mode === "login" && isAuthenticated) return null;

  return <>{children}</>;
}
