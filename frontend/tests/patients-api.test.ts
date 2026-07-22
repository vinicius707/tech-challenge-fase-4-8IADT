import { describe, expect, it } from "vitest";

import { formatPatientLabel, parsePatientList } from "@/lib/patients/api";

describe("patients api helpers", () => {
  it("parseia lista da API", () => {
    const items = parsePatientList({
      items: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          code: "PAC-001",
          has_sensitive_label: true,
          sensitive_label_masked: "********",
          created_at: "2026-07-21T12:00:00Z",
          updated_at: "2026-07-21T12:00:00Z",
        },
      ],
    });
    expect(items).toHaveLength(1);
    expect(items[0].code).toBe("PAC-001");
    expect(items[0].sensitiveLabelMasked).toBe("********");
  });

  it("formata rótulo mascarado ou ausente", () => {
    expect(
      formatPatientLabel({
        hasSensitiveLabel: true,
        sensitiveLabelMasked: "********",
      }),
    ).toBe("********");
    expect(
      formatPatientLabel({
        hasSensitiveLabel: false,
        sensitiveLabelMasked: null,
      }),
    ).toBe("—");
  });
});
