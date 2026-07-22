import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createCaseWithVitals,
  createIdempotencyKey,
  messageForCreateCaseError,
  parseCreatedCase,
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
});
