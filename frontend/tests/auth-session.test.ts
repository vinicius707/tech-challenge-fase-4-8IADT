import { describe, expect, it } from "vitest";

import { createSessionStore } from "@/lib/auth/session";

describe("session store", () => {
  it("começa sem sessão autenticada", () => {
    const store = createSessionStore();
    expect(store.getState().accessToken).toBeNull();
    expect(store.getState().isAuthenticated()).toBe(false);
  });

  it("persiste tokens e identidade após login", () => {
    const store = createSessionStore();
    store.getState().setSession({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      username: "medico",
      role: "medico",
    });

    const state = store.getState();
    expect(state.accessToken).toBe("access-1");
    expect(state.refreshToken).toBe("refresh-1");
    expect(state.username).toBe("medico");
    expect(state.role).toBe("medico");
    expect(state.isAuthenticated()).toBe(true);
  });

  it("limpa sessão no logout", () => {
    const store = createSessionStore();
    store.getState().setSession({
      accessToken: "access-1",
      refreshToken: "refresh-1",
      username: "medico",
      role: "medico",
    });
    store.getState().clearSession();

    expect(store.getState().accessToken).toBeNull();
    expect(store.getState().refreshToken).toBeNull();
    expect(store.getState().username).toBeNull();
    expect(store.getState().role).toBeNull();
    expect(store.getState().isAuthenticated()).toBe(false);
  });
});
