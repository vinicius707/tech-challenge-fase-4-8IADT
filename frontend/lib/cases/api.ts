import { apiFetch } from "@/lib/auth/client";

export type CreatedCase = {
  id: string;
  patientId: string;
  status: string;
};

type CreatedCaseApi = {
  id: string;
  patient_id: string;
  status: string;
};

export function parseCreatedCase(body: CreatedCaseApi): CreatedCase {
  return {
    id: body.id,
    patientId: body.patient_id,
    status: body.status,
  };
}

export function createIdempotencyKey(): string {
  return crypto.randomUUID();
}

export function messageForCreateCaseError(status: number): string {
  if (status === 401) {
    return "Sessão expirada. Faça login novamente.";
  }
  if (status === 404) {
    return "Paciente não encontrado.";
  }
  if (status === 503) {
    return "Armazenamento indisponível. Tente novamente.";
  }
  return `Falha ao criar Caso (${status}).`;
}

export async function createCaseWithVitals(
  patientId: string,
  file: File,
  idempotencyKey: string,
): Promise<CreatedCase> {
  const form = new FormData();
  form.append("file", file);

  const response = await apiFetch(`/api/patients/${patientId}/cases`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: form,
  });

  if (!response.ok) {
    throw new Error(messageForCreateCaseError(response.status));
  }

  const body = (await response.json()) as CreatedCaseApi;
  return parseCreatedCase(body);
}
