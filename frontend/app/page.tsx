export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Limen</h1>
      <p className="text-muted-foreground max-w-md text-center text-sm">
        Protótipo acadêmico — não é um dispositivo médico. Shell frontend
        (Épico 4): Next.js, Tailwind e shadcn/ui com proxy{" "}
        <code className="text-foreground">/api</code> → FastAPI.
      </p>
    </main>
  );
}
