/** TDD T7.10 — UI admin Falhas de Processamento (DLQ). */

import { describe, expect, it } from "vitest";

import {
  messageForFailureActionError,
  parseFailure,
  parseFailureList,
} from "@/lib/failures/api";
import {
  isNavItemVisible,
  primaryNavItems,
} from "@/lib/shell/nav";

describe("failures api helpers (T7.10)", () => {
  it("parseia lista e detalhe da API", () => {
    const items = parseFailureList({
      items: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          case_id: "22222222-2222-2222-2222-222222222222",
          patient_id: "33333333-3333-3333-3333-333333333333",
          modality: "audio",
          error_summary: "RuntimeError: boom",
          attempts: 3,
          status: "open",
          created_at: "2026-07-22T12:00:00Z",
          updated_at: "2026-07-22T12:00:00Z",
        },
      ],
    });
    expect(items).toHaveLength(1);
    expect(items[0].modality).toBe("audio");
    expect(items[0].errorSummary).toBe("RuntimeError: boom");
    expect(items[0].status).toBe("open");

    const detail = parseFailure({
      id: "11111111-1111-1111-1111-111111111111",
      case_id: "22222222-2222-2222-2222-222222222222",
      patient_id: "33333333-3333-3333-3333-333333333333",
      modality: "audio",
      error_summary: "RuntimeError: boom",
      attempts: 3,
      status: "open",
      created_at: "2026-07-22T12:00:00Z",
      updated_at: "2026-07-22T12:00:00Z",
    });
    expect(detail.caseId).toBe("22222222-2222-2222-2222-222222222222");
  });

  it("mapeia erros HTTP de ações DLQ", () => {
    expect(messageForFailureActionError(403)).toMatch(/permissão|admin/i);
    expect(messageForFailureActionError(404)).toMatch(/não encontrada/i);
    expect(messageForFailureActionError(409)).toMatch(/aberta/i);
  });
});

describe("shell nav admin (T7.10)", () => {
  it("habilita /admin/falhas só para papel admin", () => {
    const admin = primaryNavItems.find((i) => i.href === "/admin/falhas");
    expect(admin?.enabled).toBe(true);
    expect(admin?.roles).toEqual(["admin"]);
    expect(isNavItemVisible(admin!, "admin")).toBe(true);
    expect(isNavItemVisible(admin!, "medico")).toBe(false);
    expect(isNavItemVisible(admin!, null)).toBe(false);
  });
});
