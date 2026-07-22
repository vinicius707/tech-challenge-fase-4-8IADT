import { AuthGate } from "@/components/auth/auth-gate";
import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <AuthGate mode="login">
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
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
