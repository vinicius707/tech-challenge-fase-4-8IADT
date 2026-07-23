import { apiFetch } from "@/lib/auth/client";

export type Patient = {
  id: string;
  code: string;
  hasSensitiveLabel: boolean;
  sensitiveLabelMasked: string | null;
  createdAt: string;
  updatedAt: string;
};

export type SensitiveLabelReveal = {
  id: string;
  code: string;
  sensitiveLabel: string;
  revealedAt: string;
};

type PatientApiItem = {
  id: string;
  code: string;
  has_sensitive_label: boolean;
  sensitive_label_masked: string | null;
  created_at: string;
  updated_at: string;
};

type PatientListApi = {
  items: PatientApiItem[];
};

type SensitiveLabelRevealApi = {
  id: string;
  code: string;
  sensitive_label: string;
  revealed_at: string;
};

function mapPatient(item: PatientApiItem): Patient {
  return {
    id: item.id,
    code: item.code,
    hasSensitiveLabel: item.has_sensitive_label,
    sensitiveLabelMasked: item.sensitive_label_masked,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

export function parsePatientList(body: PatientListApi): Patient[] {
  return (body.items ?? []).map(mapPatient);
}

export function parseSensitiveLabelReveal(
  body: SensitiveLabelRevealApi,
): SensitiveLabelReveal {
  return {
    id: body.id,
    code: body.code,
    sensitiveLabel: body.sensitive_label,
    revealedAt: body.revealed_at,
  };
}

export function formatPatientLabel(patient: {
  hasSensitiveLabel: boolean;
  sensitiveLabelMasked: string | null;
}): string {
  if (patient.hasSensitiveLabel && patient.sensitiveLabelMasked) {
    return patient.sensitiveLabelMasked;
  }
  return "—";
}

export function formatSensitiveLabelAnnouncement(
  state: "revealed" | "masked",
  plaintext?: string,
): string {
  if (state === "revealed") {
    return `Rótulo Sensível revelado: ${plaintext ?? ""}.`;
  }
  return "Rótulo Sensível remascarado.";
}

export async function fetchPatients(): Promise<Patient[]> {
  const response = await apiFetch("/api/patients");
  if (!response.ok) {
    throw new Error(`Falha ao listar Pacientes (${response.status})`);
  }
  const body = (await response.json()) as PatientListApi;
  return parsePatientList(body);
}

export async function fetchPatient(patientId: string): Promise<Patient> {
  const response = await apiFetch(`/api/patients/${patientId}`);
  if (response.status === 404) {
    throw new Error("Paciente não encontrado");
  }
  if (!response.ok) {
    throw new Error(`Falha ao obter Paciente (${response.status})`);
  }
  const body = (await response.json()) as PatientApiItem;
  return mapPatient(body);
}

export async function createPatient(): Promise<Patient> {
  const response = await apiFetch("/api/patients", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error(`Falha ao criar Paciente (${response.status})`);
  }
  const body = (await response.json()) as PatientApiItem;
  return mapPatient(body);
}

export async function revealSensitiveLabel(
  patientId: string,
): Promise<SensitiveLabelReveal> {
  const response = await apiFetch(
    `/api/patients/${patientId}/sensitive-label/reveal`,
    { method: "POST" },
  );
  if (response.status === 404) {
    throw new Error("Rótulo Sensível não disponível");
  }
  if (response.status === 503) {
    throw new Error("Criptografia de Rótulo Sensível indisponível");
  }
  if (!response.ok) {
    throw new Error(`Falha ao revelar Rótulo Sensível (${response.status})`);
  }
  const body = (await response.json()) as SensitiveLabelRevealApi;
  return parseSensitiveLabelReveal(body);
}
