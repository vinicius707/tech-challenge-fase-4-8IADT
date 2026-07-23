"use client";

import { useEffect } from "react";

import { applyThemeClass, useThemeStore } from "@/lib/theme/store";

/** Sincroniza a preferência Zustand com a classe `.dark` no `<html>`. */
export function ThemeSync() {
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    applyThemeClass(theme, document.documentElement);
  }, [theme]);

  return null;
}
