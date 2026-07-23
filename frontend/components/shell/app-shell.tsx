"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { LogoutButton } from "@/components/auth/logout-button";
import { AlertsStreamBridge } from "@/components/alerts/alerts-stream-bridge";
import { AlertsStreamIndicator } from "@/components/alerts/alerts-stream-indicator";
import { AlertsToast } from "@/components/alerts/alerts-toast";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { primaryNavItems, isNavItemVisible } from "@/lib/shell/nav";
import { useSessionStore } from "@/lib/auth/session";
import { cn } from "@/lib/utils";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const username = useSessionStore((s) => s.username);
  const role = useSessionStore((s) => s.role);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <AlertsStreamBridge />
      <AlertsToast />
      <header className="border-b border-border">
        <div className="mx-auto flex w-full max-w-6xl items-center gap-3 px-4 py-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="md:hidden"
            aria-expanded={mobileOpen}
            aria-controls="nav-principal"
            onClick={() => setMobileOpen((open) => !open)}
          >
            Menu
          </Button>
          <p className="text-lg font-semibold tracking-tight">Limen</p>
          <div className="ml-auto flex min-w-0 items-center gap-3">
            <AlertsStreamIndicator />
            <ThemeToggle />
            <p className="truncate text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{username}</span>
              {role ? (
                <span className="text-muted-foreground"> · {role}</span>
              ) : null}
            </p>
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col md:flex-row">
        <nav
          id="nav-principal"
          aria-label="Principal"
          className={cn(
            "border-b border-border px-4 py-3 md:w-56 md:shrink-0 md:border-b-0 md:border-r md:py-6",
            mobileOpen ? "block" : "hidden md:block",
          )}
        >
          <ul className="flex flex-col gap-1">
            {primaryNavItems.map((item) => {
              const visible = isNavItemVisible(item, role);
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              if (!item.enabled) {
                return (
                  <li key={item.href}>
                    <span
                      className="block rounded-md px-3 py-2 text-sm text-muted-foreground/70"
                      aria-disabled="true"
                      title="Disponível em épico futuro"
                    >
                      {item.label}
                    </span>
                  </li>
                );
              }
              if (!visible) {
                return null;
              }
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      "block rounded-md px-3 py-2 text-sm transition-colors",
                      active
                        ? "bg-muted font-medium text-foreground"
                        : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                    )}
                    onClick={() => setMobileOpen(false)}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <main id="conteudo-principal" className="min-w-0 flex-1 px-4 py-6">
          {children}
        </main>
      </div>
    </div>
  );
}
