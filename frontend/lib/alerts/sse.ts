/**
 * Cliente SSE de Alertas via fetch + ReadableStream (ADR 0022).
 * Não usa EventSource nem token na query string.
 */

export const ALERTS_STREAM_PATH = "/api/alerts/stream";

export type AlertSsePayload = {
  alertId: string;
  caseId: string;
  level: string;
  version: number;
  createdAt: string;
};

export type AlertSseMessage = {
  event: string;
  data: AlertSsePayload;
};

type AlertSsePayloadApi = {
  alert_id: string;
  case_id: string;
  level: string;
  version: number;
  created_at: string;
};

export function alertsStreamUrl(): string {
  return ALERTS_STREAM_PATH;
}

export function authorizationHeader(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

export function nextReconnectDelayMs(
  attempt: number,
  baseMs = 500,
  maxMs = 8_000,
): number {
  const delay = baseMs * 2 ** Math.max(0, attempt);
  return Math.min(maxMs, delay);
}

function parsePayload(raw: AlertSsePayloadApi): AlertSsePayload {
  return {
    alertId: raw.alert_id,
    caseId: raw.case_id,
    level: raw.level,
    version: raw.version,
    createdAt: raw.created_at,
  };
}

/**
 * Extrai mensagens SSE completas (separadas por linha em branco) de um buffer.
 * Comentários (`:`) e heartbeats são ignorados.
 */
export function parseSseBuffer(buffer: string): {
  messages: AlertSseMessage[];
  rest: string;
} {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  const messages: AlertSseMessage[] = [];

  for (const block of parts) {
    const lines = block.split("\n");
    let event = "message";
    let dataLine: string | null = null;
    for (const line of lines) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("event:")) {
        event = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataLine = line.slice("data:".length).trim();
      }
    }
    if (!dataLine) continue;
    try {
      const raw = JSON.parse(dataLine) as AlertSsePayloadApi;
      messages.push({ event, data: parsePayload(raw) });
    } catch {
      // bloco incompleto/inválido — ignora
    }
  }

  return { messages, rest };
}

export async function* readAlertSse(
  response: Response,
): AsyncGenerator<AlertSseMessage> {
  if (!response.body) {
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseBuffer(buffer);
    buffer = parsed.rest;
    for (const message of parsed.messages) {
      yield message;
    }
  }
}

export type ConnectAlertsStreamOptions = {
  accessToken: string;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
};

/**
 * Abre o stream autenticado. O chamador cuida do loop de reconexão.
 */
export async function connectAlertsStream(
  options: ConnectAlertsStreamOptions,
): Promise<Response> {
  const fetchImpl = options.fetchImpl ?? fetch;
  return fetchImpl(alertsStreamUrl(), {
    method: "GET",
    headers: authorizationHeader(options.accessToken),
    signal: options.signal,
  });
}
