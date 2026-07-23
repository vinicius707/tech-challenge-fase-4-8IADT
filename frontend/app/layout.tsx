import type { Metadata } from "next";

import { Providers } from "@/components/providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme/store";

import "./globals.css";

export const metadata: Metadata = {
  title: "Limen",
  description:
    "Protótipo acadêmico FIAP 8IADT — análise multimodal de risco clínico. Não é um dispositivo médico.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
