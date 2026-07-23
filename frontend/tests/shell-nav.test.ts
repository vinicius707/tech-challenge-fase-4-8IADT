import { describe, expect, it } from "vitest";

import { isNavItemVisible, primaryNavItems } from "@/lib/shell/nav";

describe("shell navigation", () => {
  it("inclui Pacientes, Alertas e Falhas (admin) ativos", () => {
    const byHref = Object.fromEntries(
      primaryNavItems.map((item) => [item.href, item]),
    );

    expect(byHref["/"].label).toBe("Início");
    expect(byHref["/"].enabled).toBe(true);

    expect(byHref["/pacientes"].label).toBe("Pacientes");
    expect(byHref["/pacientes"].enabled).toBe(true);

    expect(byHref["/alertas"].enabled).toBe(true);
    expect(byHref["/admin/falhas"].enabled).toBe(true);
    expect(isNavItemVisible(byHref["/admin/falhas"], "admin")).toBe(true);
    expect(isNavItemVisible(byHref["/admin/falhas"], "medico")).toBe(false);
  });

  it("expõe landmarks esperados pelo shell", () => {
    expect(primaryNavItems.every((item) => item.label.length > 0)).toBe(true);
  });
});
