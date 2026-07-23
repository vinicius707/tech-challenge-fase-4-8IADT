import { apiFetch } from "@/lib/auth/client";

export type ProcessingFailure = {
  id: string;
  caseId: string;
  patientId: string;
  modality: string;
  errorSummary: string;
  attempts: number;
  status: string;
  createdAt: string;
  updatedAt: string;
};

type FailureApi = {
  id: string;
  case_id: string;
  patient_id: string;
  modality: string;
  error_summary: string;
  attempts: number;
  status: string;
  created_at: string;
  updated_at: string;
};

type FailureListApi = {
  items: FailureApi[];
};

export function parseFailure(body: FailureApi): ProcessingFailure {
  return {
    id: body.id,
    caseId: body.case_id,
    patientId: body.patient_id,
    modality: body.modality,
    errorSummary: body.error_summary,
    attempts: body.attempts,
    status: body.status,
    createdAt: body.created_at,
    updatedAt: body.updated_at,
  };
}

export function parseFailureList(body: FailureListApi): ProcessingFailure[] {
  return (body.items ?? []).map(parseFailure);
}

export function messageForFailureActionError(status: number): string {
  if (status === 403) {
    return "Sem permissão. Apenas admin opera Falhas de Processamento.";
  }
  if (status === 404) {
    return "Falha de Processamento não encontrada.";
  }
  if (status === 409) {
    return "Falha de Processamento não está aberta.";
  }
  return `Falha na operação DLQ (${status}).`;
}

export async function fetchOpenFailures(): Promise<ProcessingFailure[]> {
  const response = await apiFetch("/api/admin/failures");
  if (response.status === 403) {
    throw new Error(messageForFailureActionError(403));
  }
  if (!response.ok) {
    throw new Error(`Falha ao listar Falhas (${response.status})`);
  }
  const body = (await response.json()) as FailureListApi;
  return parseFailureList(body);
}

export async function fetchFailure(
  failureId: string,
): Promise<ProcessingFailure> {
  const response = await apiFetch(`/api/admin/failures/${failureId}`);
  if (!response.ok) {
    throw new Error(messageForFailureActionError(response.status));
  }
  const body = (await response.json()) as FailureApi;
  return parseFailure(body);
}

export async function redriveFailure(
  failureId: string,
): Promise<ProcessingFailure> {
  const response = await apiFetch(`/api/admin/failures/${failureId}/redrive`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(messageForFailureActionError(response.status));
  }
  const body = (await response.json()) as FailureApi;
  return parseFailure(body);
}

export async function discardFailure(
  failureId: string,
): Promise<ProcessingFailure> {
  const response = await apiFetch(`/api/admin/failures/${failureId}/discard`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(messageForFailureActionError(response.status));
  }
  const body = (await response.json()) as FailureApi;
  return parseFailure(body);
}
