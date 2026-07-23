/** TDD T7.8 — uploads a11y + anúncios de reveal do Rótulo Sensível. */

import { describe, expect, it } from "vitest";

import {
  uploadFieldDescribedBy,
  uploadFieldIds,
} from "@/lib/a11y/upload-field";
import {
  messageForAttachModalityError,
  modalityUploadPath,
} from "@/lib/cases/api";
import {
  formatSensitiveLabelAnnouncement,
  parseSensitiveLabelReveal,
} from "@/lib/patients/api";

describe("upload field a11y helpers (T7.8)", () => {
  it("gera ids estáveis por campo", () => {
    const ids = uploadFieldIds("vitals");
    expect(ids.inputId).toBe("upload-vitals");
    expect(ids.hintId).toBe("upload-vitals-hint");
    expect(ids.errorId).toBe("upload-vitals-error");
    expect(ids.successId).toBe("upload-vitals-success");
  });

  it("associa hint + erro via aria-describedby", () => {
    const ids = uploadFieldIds("video");
    expect(uploadFieldDescribedBy({ hintId: ids.hintId, errorId: null })).toBe(
      ids.hintId,
    );
    expect(
      uploadFieldDescribedBy({ hintId: ids.hintId, errorId: ids.errorId }),
    ).toBe(`${ids.hintId} ${ids.errorId}`);
    expect(
      uploadFieldDescribedBy({
        hintId: ids.hintId,
        errorId: null,
        successId: ids.successId,
      }),
    ).toBe(`${ids.hintId} ${ids.successId}`);
  });
});

describe("sensitive label SR announcements (T7.8)", () => {
  it("anuncia desmascarar e remascarar", () => {
    expect(formatSensitiveLabelAnnouncement("revealed", "Paciente Demo")).toBe(
      "Rótulo Sensível revelado: Paciente Demo.",
    );
    expect(formatSensitiveLabelAnnouncement("masked")).toBe(
      "Rótulo Sensível remascarado.",
    );
  });
});

describe("modality upload API helpers (T7.8)", () => {
  it("monta paths de anexo sem token na query", () => {
    expect(modalityUploadPath("case-1", "video")).toBe(
      "/api/cases/case-1/modalities/video",
    );
    expect(modalityUploadPath("case-1", "audio")).toBe(
      "/api/cases/case-1/modalities/audio",
    );
    expect(modalityUploadPath("case-1", "prescriptions")).toBe(
      "/api/cases/case-1/modalities/prescriptions",
    );
  });

  it("mapeia erros HTTP de anexo", () => {
    expect(messageForAttachModalityError(400)).toContain("Idempotency-Key");
    expect(messageForAttachModalityError(409)).toContain("já");
    expect(messageForAttachModalityError(503)).toContain("Armazenamento");
  });
});

describe("sensitive label reveal parse (T7.8)", () => {
  it("parseia resposta do reveal", () => {
    const revealed = parseSensitiveLabelReveal({
      id: "11111111-1111-1111-1111-111111111111",
      code: "PAC-001",
      sensitive_label: "Paciente Demo",
      revealed_at: "2026-07-22T12:00:00Z",
    });
    expect(revealed.sensitiveLabel).toBe("Paciente Demo");
    expect(revealed.code).toBe("PAC-001");
    expect(revealed.revealedAt).toBe("2026-07-22T12:00:00Z");
  });
});
