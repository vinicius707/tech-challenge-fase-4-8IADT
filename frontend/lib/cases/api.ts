import { apiFetch } from "@/lib/auth/client";

/** Intervalo de polling enquanto o Caso não é terminal. */
export const CASE_POLL_INTERVAL_MS = 2_000;

/**
 * Timeout de UX: após este tempo sem `done`/`failed`/`cancelled`, a UI para
 * de fazer polling (sem DLQ). O worker pode continuar no backend.
 */
export const CASE_POLL_TIMEOUT_MS = 120_000;

export type CreatedCase = {
  id: string;
  patientId: string;
  status: string;
};

export type CaseModality = {
  modality: string;
  status: string;
  artifactId: string | null;
};

export type CaseAlert = {
  id: string;
  caseId: string;
  level: string;
  version: number;
  createdAt: string;
};

export type CaseJustificationModality = {
  modality: string;
  status: string;
  weight: number | null;
  partialScore: number | null;
  partialLevel: string | null;
  topAnomalies: string[];
};

export type CaseJustification = {
  narrative: string;
  modalities: CaseJustificationModality[];
};

export type CaseDetail = {
  id: string;
  patientId: string;
  status: string;
  riskScore: number | null;
  riskLevel: string | null;
  modalities: CaseModality[];
  alerts: CaseAlert[];
  justification: CaseJustification | null;
};

type CreatedCaseApi = {
  id: string;
  patient_id: string;
  status: string;
};

type CaseModalityApi = {
  modality: string;
  status: string;
  artifact_id: string | null;
};

type CaseAlertApi = {
  id: string;
  case_id: string;
  level: string;
  version: number;
  created_at: string;
};

type CaseJustificationModalityApi = {
  modality: string;
  status: string;
  weight: number | null;
  partial_score: number | null;
  partial_level: string | null;
  top_anomalies: string[];
};

type CaseJustificationApi = {
  narrative: string;
  modalities: CaseJustificationModalityApi[];
};

type CaseDetailApi = {
  id: string;
  patient_id: string;
  status: string;
  risk_score: number | null;
  risk_level: string | null;
  modalities?: CaseModalityApi[];
  alerts?: CaseAlertApi[];
  justification?: CaseJustificationApi | null;
};

export function parseCreatedCase(body: CreatedCaseApi): CreatedCase {
  return {
    id: body.id,
    patientId: body.patient_id,
    status: body.status,
  };
}

export function parseCaseDetail(body: CaseDetailApi): CaseDetail {
  const justificationRaw = body.justification ?? null;
  return {
    id: body.id,
    patientId: body.patient_id,
    status: body.status,
    riskScore: body.risk_score,
    riskLevel: body.risk_level,
    modalities: (body.modalities ?? []).map((m) => ({
      modality: m.modality,
      status: m.status,
      artifactId: m.artifact_id,
    })),
    alerts: (body.alerts ?? []).map((a) => ({
      id: a.id,
      caseId: a.case_id,
      level: a.level,
      version: a.version,
      createdAt: a.created_at,
    })),
    justification: justificationRaw
      ? {
          narrative: justificationRaw.narrative,
          modalities: justificationRaw.modalities.map((m) => ({
            modality: m.modality,
            status: m.status,
            weight: m.weight,
            partialScore: m.partial_score,
            partialLevel: m.partial_level,
            topAnomalies: m.top_anomalies ?? [],
          })),
        }
      : null,
  };
}

export function isCaseTerminal(status: string): boolean {
  return status === "done" || status === "failed" || status === "cancelled";
}

export function shouldPollCase(status: string): boolean {
  return status === "pending" || status === "processing";
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

export async function fetchCase(caseId: string): Promise<CaseDetail> {
  const response = await apiFetch(`/api/cases/${caseId}`);
  if (response.status === 404) {
    throw new Error("Caso não encontrado");
  }
  if (!response.ok) {
    throw new Error(`Falha ao obter Caso (${response.status})`);
  }
  const body = (await response.json()) as CaseDetailApi;
  return parseCaseDetail(body);
}
