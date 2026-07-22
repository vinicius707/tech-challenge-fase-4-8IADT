"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { logout as logoutRequest } from "@/lib/auth/api";
import { useSessionStore } from "@/lib/auth/session";

export function LogoutButton() {
  const router = useRouter();
  const accessToken = useSessionStore((s) => s.accessToken);
  const refreshToken = useSessionStore((s) => s.refreshToken);
  const clearSession = useSessionStore((s) => s.clearSession);
  const [pending, setPending] = useState(false);

  async function onLogout() {
    setPending(true);
    try {
      if (accessToken) {
        try {
          await logoutRequest({
            accessToken,
            refreshToken,
          });
        } catch {
          // Limpa sessão local mesmo se a API falhar (rede).
        }
      }
      clearSession();
      router.replace("/login");
    } finally {
      setPending(false);
    }
  }

  return (
    <Button
      type="button"
      variant="outline"
      onClick={onLogout}
      disabled={pending}
    >
      {pending ? "Saindo…" : "Sair"}
    </Button>
  );
}
