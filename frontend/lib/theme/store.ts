import { createStore } from "zustand/vanilla";
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark";

export const THEME_STORAGE_KEY = "limen-theme";

export type ThemeState = {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
};

type ThemeRoot = {
  classList: {
    add: (value: string) => void;
    remove: (value: string) => void;
    contains: (value: string) => boolean;
  };
};

function themeActions(
  set: (
    partial:
      | Partial<ThemeState>
      | ((state: ThemeState) => Partial<ThemeState>),
  ) => void,
  get: () => ThemeState,
): Pick<ThemeState, "setTheme" | "toggleTheme"> {
  return {
    setTheme: (theme) => set({ theme }),
    toggleTheme: () =>
      set({ theme: get().theme === "dark" ? "light" : "dark" }),
  };
}

/** Store sem persist — para testes unitários. */
export function createThemeStore(initial: ThemeMode = "light") {
  return createStore<ThemeState>()((set, get) => ({
    theme: initial,
    ...themeActions(set, get),
  }));
}

/** Preferência de tema (ADR 0025) com persistência local. */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "light",
      ...themeActions(set, get),
    }),
    {
      name: THEME_STORAGE_KEY,
      partialize: (state) => ({ theme: state.theme }),
    },
  ),
);

export function applyThemeClass(theme: ThemeMode, root: ThemeRoot): void {
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export function parsePersistedTheme(raw: string | null): ThemeMode {
  if (!raw) return "light";
  try {
    const parsed = JSON.parse(raw) as { state?: { theme?: unknown } };
    return parsed.state?.theme === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

/** Script inline para evitar FOUC antes da hidratação React. */
export const THEME_INIT_SCRIPT = `(function(){try{var r=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});if(!r)return;var t=JSON.parse(r);if(t&&t.state&&t.state.theme==="dark")document.documentElement.classList.add("dark");}catch(e){}})();`;
