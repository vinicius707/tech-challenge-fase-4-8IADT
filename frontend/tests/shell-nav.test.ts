import { describe, expect, it } from "vitest";

import { primaryNavItems } from "@/lib/shell/nav";

describe("shell navigation", () => {
  it("inclui Pacientes e Alertas ativos; Admin permanece placeholder", () => {
    const byHref = Object.fromEntries(
      primaryNavItems.map((item) => [item.href, item]),
    );

    expect(byHref["/"].label).toBe("Início");
    expect(byHref["/"].enabled).toBe(true);

    expect(byHref["/pacientes"].label).toBe("Pacientes");
    expect(byHref["/pacientes"].enabled).toBe(true);

    expect(byHref["/alertas"].enabled).toBe(true);
    expect(byHref["/admin/falhas"].enabled).toBe(false);
  });

  it("expõe landmarks esperados pelo shell", () => {
    expect(primaryNavItems.every((item) => item.label.length > 0)).toBe(true);
  });
});
