import { describe, expect, it } from "vitest";

import {
  applyThemeClass,
  createThemeStore,
  THEME_STORAGE_KEY,
  parsePersistedTheme,
} from "@/lib/theme/store";

describe("theme store (T7.6)", () => {
  it("começa em light", () => {
    const store = createThemeStore();
    expect(store.getState().theme).toBe("light");
  });

  it("alterna entre light e dark", () => {
    const store = createThemeStore();
    store.getState().toggleTheme();
    expect(store.getState().theme).toBe("dark");
    store.getState().toggleTheme();
    expect(store.getState().theme).toBe("light");
  });

  it("setTheme define o modo explicitamente", () => {
    const store = createThemeStore();
    store.getState().setTheme("dark");
    expect(store.getState().theme).toBe("dark");
    store.getState().setTheme("light");
    expect(store.getState().theme).toBe("light");
  });

  it("aplica a classe dark no root conforme o tema", () => {
    const classes = new Set<string>();
    const root = {
      classList: {
        add: (value: string) => {
          classes.add(value);
        },
        remove: (value: string) => {
          classes.delete(value);
        },
        contains: (value: string) => classes.has(value),
      },
    };

    applyThemeClass("dark", root);
    expect(root.classList.contains("dark")).toBe(true);
    applyThemeClass("light", root);
    expect(root.classList.contains("dark")).toBe(false);
  });

  it("lê tema persistido no formato Zustand a partir do storage key estável", () => {
    expect(THEME_STORAGE_KEY).toBe("limen-theme");
    expect(
      parsePersistedTheme(
        JSON.stringify({ state: { theme: "dark" }, version: 0 }),
      ),
    ).toBe("dark");
    expect(
      parsePersistedTheme(
        JSON.stringify({ state: { theme: "light" }, version: 0 }),
      ),
    ).toBe("light");
    expect(parsePersistedTheme(null)).toBe("light");
    expect(parsePersistedTheme("{broken")).toBe("light");
  });
});
