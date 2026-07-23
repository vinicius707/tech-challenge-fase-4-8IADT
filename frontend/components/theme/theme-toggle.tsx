"use client";

import { Button } from "@/components/ui/button";
import { useThemeStore } from "@/lib/theme/store";

export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const next = theme === "dark" ? "claro" : "escuro";

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={toggleTheme}
      aria-label={`Ativar tema ${next}`}
      title={`Tema ${theme === "dark" ? "escuro" : "claro"}`}
    >
      {theme === "dark" ? "Claro" : "Escuro"}
    </Button>
  );
}
