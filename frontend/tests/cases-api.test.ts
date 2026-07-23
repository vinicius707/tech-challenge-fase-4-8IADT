import { afterEach, describe, expect, it, vi } from "vitest";

import {
  CASE_POLL_INTERVAL_MS,
  CASE_POLL_TIMEOUT_MS,
  createCaseWithVitals,
  createIdempotencyKey,
  fetchCase,
  isCaseTerminal,
  messageForCreateCaseError,
  parseCaseDetail,
  parseCreatedCase,
  shouldPollCase,
} from "@/lib/cases/api";

vi.mock("@/lib/auth/client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/auth/client";

const apiFetchMock = vi.mocked(apiFetch);

describe("cases api helpers", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("parseia Caso criado a partir da API", () => {
    const created = parseCreatedCase({
      id: "22222222-2222-2222-2222-222222222222",
      patient_id: "11111111-1111-1111-1111-111111111111",
      status: "pending",
    });
    expect(created.id).toBe("22222222-2222-2222-2222-222222222222");
    expect(created.patientId).toBe("11111111-1111-1111-1111-111111111111");
    expect(created.status).toBe("pending");
  });

  it("gera Idempotency-Key não vazia por tentativa", () => {
    const a = createIdempotencyKey();
    const b = createIdempotencyKey();
    expect(a.length).toBeGreaterThan(8);
    expect(b.length).toBeGreaterThan(8);
    expect(a).not.toBe(b);
  });

  it("mapeia erros de API para feedback visível", () => {
    expect(messageForCreateCaseError(401)).toMatch(/sessão|login/i);
    expect(messageForCreateCaseError(404)).toMatch(/paciente/i);
    expect(messageForCreateCaseError(503)).toMatch(/armazenamento|indispon/i);
    expect(messageForCreateCaseError(500)).toMatch(/falha/i);
  });

  it("envia CSV com Idempotency-Key e devolve case_id", async () => {
    apiFetchMock.mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        id: "33333333-3333-3333-3333-333333333333",
        patient_id: "11111111-1111-1111-1111-111111111111",
        status: "pending",
      }),
    } as Response);

    const file = new File(["hr,spo2\n80,98\n"], "vitals.csv", {
      type: "text/csv",
    });
    const created = await createCaseWithVitals(
      "11111111-1111-1111-1111-111111111111",
      file,
      "key-attempt-1",
    );

    expect(created.id).toBe("33333333-3333-3333-3333-333333333333");
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/patients/11111111-1111-1111-1111-111111111111/cases",
      expect.objectContaining({
        method: "POST",
        headers: { "Idempotency-Key": "key-attempt-1" },
      }),
    );
    const init = apiFetchMock.mock.calls[0][1] as RequestInit;
    expect(init.body).toBeInstanceOf(FormData);
    const form = init.body as FormData;
    expect(form.get("file")).toBeInstanceOf(File);
  });

  it("propaga erro 404 de Paciente", async () => {
    apiFetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Paciente não encontrado" }),
    } as Response);

    const file = new File(["hr\n80\n"], "vitals.csv", { type: "text/csv" });
    await expect(
      createCaseWithVitals("missing", file, "k"),
    ).rejects.toThrow(/paciente/i);
  });

  it("parseia detalhe com Risco e Alertas", () => {
    const detail = parseCaseDetail({
      id: "22222222-2222-2222-2222-222222222222",
      patient_id: "11111111-1111-1111-1111-111111111111",
      status: "done",
      risk_score: 0.55,
      risk_level: "MEDIO",
      modalities: [{ modality: "vitals", status: "done", artifact_id: "a1" }],
      alerts: [
        {
          id: "44444444-4444-4444-4444-444444444444",
          case_id: "22222222-2222-2222-2222-222222222222",
          level: "MEDIO",
          version: 1,
          created_at: "2026-07-21T12:00:00Z",
        },
      ],
    });
    expect(detail.status).toBe("done");
    expect(detail.riskLevel).toBe("MEDIO");
    expect(detail.riskScore).toBe(0.55);
    expect(detail.modalities[0].modality).toBe("vitals");
    expect(detail.alerts).toHaveLength(1);
    expect(detail.alerts[0].level).toBe("MEDIO");
    expect(detail.alerts[0].version).toBe(1);
    expect(detail.justification).toBeNull();
  });

  it("parseia Justificativa template do Caso", () => {
    const detail = parseCaseDetail({
      id: "22222222-2222-2222-2222-222222222222",
      patient_id: "11111111-1111-1111-1111-111111111111",
      status: "done",
      risk_score: 0.55,
      risk_level: "MEDIO",
      modalities: [
        { modality: "vitals", status: "done", artifact_id: "a1" },
        { modality: "audio", status: "failed", artifact_id: null },
      ],
      alerts: [],
      justification: {
        narrative:
          "Risco MEDIO (score 0.55). Contribuições: vitals: MEDIO (0.55). Modalidades indisponíveis: audio (failed).",
        modalities: [
          {
            modality: "vitals",
            status: "done",
            weight: 1.0,
            partial_score: 0.55,
            partial_level: "MEDIO",
            top_anomalies: ["heart_rate"],
          },
          {
            modality: "audio",
            status: "failed",
            weight: null,
            partial_score: null,
            partial_level: null,
            top_anomalies: [],
          },
        ],
      },
    });
    expect(detail.justification).not.toBeNull();
    expect(detail.justification?.narrative).toMatch(/Risco MEDIO/);
    expect(detail.justification?.modalities).toHaveLength(2);
    expect(detail.justification?.modalities[0].topAnomalies).toEqual([
      "heart_rate",
    ]);
    expect(detail.justification?.modalities[1].weight).toBeNull();
  });

  it("BAIXO chega sem Alertas listados", () => {
    const detail = parseCaseDetail({
      id: "22222222-2222-2222-2222-222222222222",
      patient_id: "11111111-1111-1111-1111-111111111111",
      status: "done",
      risk_score: 0.2,
      risk_level: "BAIXO",
      modalities: [{ modality: "vitals", status: "done", artifact_id: null }],
      alerts: [],
    });
    expect(detail.riskLevel).toBe("BAIXO");
    expect(detail.alerts).toEqual([]);
  });

  it("polling só em pending/processing até timeout de UX", () => {
    expect(isCaseTerminal("done")).toBe(true);
    expect(isCaseTerminal("failed")).toBe(true);
    expect(isCaseTerminal("cancelled")).toBe(true);
    expect(isCaseTerminal("pending")).toBe(false);
    expect(shouldPollCase("pending")).toBe(true);
    expect(shouldPollCase("processing")).toBe(true);
    expect(shouldPollCase("done")).toBe(false);
    expect(CASE_POLL_INTERVAL_MS).toBe(2000);
    expect(CASE_POLL_TIMEOUT_MS).toBe(120_000);
  });

  it("fetchCase obtém detalhe por id", async () => {
    apiFetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: "22222222-2222-2222-2222-222222222222",
        patient_id: "11111111-1111-1111-1111-111111111111",
        status: "processing",
        risk_score: null,
        risk_level: null,
        modalities: [{ modality: "vitals", status: "processing", artifact_id: "a1" }],
        alerts: [],
      }),
    } as Response);

    const detail = await fetchCase("22222222-2222-2222-2222-222222222222");
    expect(detail.status).toBe("processing");
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/cases/22222222-2222-2222-2222-222222222222",
    );
  });
});
