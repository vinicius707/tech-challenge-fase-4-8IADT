import { createStore } from "zustand/vanilla";
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type OperatorRole = "medico" | "admin";

export type SessionData = {
  accessToken: string;
  refreshToken: string;
  username: string;
  role: OperatorRole;
};

export type SessionState = {
  accessToken: string | null;
  refreshToken: string | null;
  username: string | null;
  role: OperatorRole | null;
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;
  setSession: (data: SessionData) => void;
  clearSession: () => void;
  isAuthenticated: () => boolean;
};

const initialTokens = {
  accessToken: null as string | null,
  refreshToken: null as string | null,
  username: null as string | null,
  role: null as OperatorRole | null,
};

function sessionActions(
  set: (
    partial:
      | Partial<SessionState>
      | ((state: SessionState) => Partial<SessionState>),
  ) => void,
  get: () => SessionState,
): Pick<
  SessionState,
  "setHasHydrated" | "setSession" | "clearSession" | "isAuthenticated"
> {
  return {
    setHasHydrated: (hasHydrated) => set({ hasHydrated }),
    setSession: (data) =>
      set({
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
        username: data.username,
        role: data.role,
      }),
    clearSession: () => set({ ...initialTokens }),
    isAuthenticated: () => Boolean(get().accessToken),
  };
}

/** Store sem persist — para testes unitários. */
export function createSessionStore() {
  return createStore<SessionState>()((set, get) => ({
    ...initialTokens,
    hasHydrated: true,
    ...sessionActions(set, get),
  }));
}

/** Sessão do Operador (ADR 0025) com persistência local. */
export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      ...initialTokens,
      hasHydrated: false,
      ...sessionActions(set, get),
    }),
    {
      name: "limen-session",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        username: state.username,
        role: state.role,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    },
  ),
);
