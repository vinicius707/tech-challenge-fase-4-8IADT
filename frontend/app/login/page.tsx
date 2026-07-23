import dynamic from "next/dynamic";

import { AuthGate } from "@/components/auth/auth-gate";
import { LoginForm } from "@/components/auth/login-form";

const ThemeToggle = dynamic(
  () =>
    import("@/components/theme/theme-toggle").then((m) => m.ThemeToggle),
  { ssr: false },
);

export default function LoginPage() {
  return (
    <AuthGate mode="login">
      <main className="relative flex min-h-screen flex-col items-center justify-center gap-6 bg-background p-8">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Limen</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Entre com seu usuário de Operador
          </p>
        </div>
        <LoginForm />
      </main>
    </AuthGate>
  );
}
