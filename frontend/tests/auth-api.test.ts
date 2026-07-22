import { afterEach, describe, expect, it, vi } from "vitest";

import { login, logout } from "@/lib/auth/api";

describe("auth api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("login válido devolve tokens e operador", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          access_token: "a",
          refresh_token: "r",
          token_type: "bearer",
          expires_in: 900,
          operator: {
            id: "11111111-1111-1111-1111-111111111111",
            username: "medico",
            role: "medico",
          },
        }),
      }),
    );

    const result = await login("medico", "medico_dev_only");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.data.accessToken).toBe("a");
    expect(result.data.refreshToken).toBe("r");
    expect(result.data.username).toBe("medico");
    expect(result.data.role).toBe("medico");
    expect(fetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("login inválido não grava sessão e sinaliza erro", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Credenciais inválidas" }),
      }),
    );

    const result = await login("medico", "wrong");
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.status).toBe(401);
    expect(result.message).toMatch(/credenciais|inválid/i);
  });

  it("logout chama API com Bearer e refresh", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        json: async () => ({}),
      }),
    );

    await logout({ accessToken: "a", refreshToken: "r" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer a",
        }),
      }),
    );
  });
});
