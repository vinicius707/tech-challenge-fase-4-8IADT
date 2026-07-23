"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";

import { ThemeSync } from "@/components/theme/theme-sync";

const AppDataProviders = dynamic(
  () =>
    import("@/components/app-data-providers").then((m) => m.AppDataProviders),
  { ssr: true },
);

export function Providers({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  return (
    <>
      <ThemeSync />
      {isLogin ? children : <AppDataProviders>{children}</AppDataProviders>}
    </>
  );
}
