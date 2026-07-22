/**
 * Rewrite `/api/*` → backend FastAPI (ADR 0023).
 * O prefixo `/api` é removido no destino.
 */
export function apiRewrites(backendUrl) {
  const origin = (backendUrl || "http://localhost:8000").replace(/\/$/, "");
  return [
    {
      source: "/api/:path*",
      destination: `${origin}/:path*`,
    },
  ];
}
