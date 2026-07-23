/** TDD T7.4 — cliente SSE de Alertas via fetch + Bearer (ADR 0022). */

import { describe, expect, it, vi } from "vitest";

import {
  ALERTS_STREAM_PATH,
  alertsStreamUrl,
  authorizationHeader,
  nextReconnectDelayMs,
  parseSseBuffer,
} from "@/lib/alerts/sse";

describe("alerts SSE client helpers", () => {
  it("usa path sem token na query (ADR 0022)", () => {
    expect(ALERTS_STREAM_PATH).toBe("/api/alerts/stream");
    expect(alertsStreamUrl()).toBe("/api/alerts/stream");
    expect(alertsStreamUrl()).not.toMatch(/[?&](token|access_token)=/i);
  });

  it("monta Authorization Bearer sem query", () => {
    const headers = new Headers(authorizationHeader("jwt-abc"));
    expect(headers.get("Authorization")).toBe("Bearer jwt-abc");
  });

  it("parseia blocos SSE event/data e ignora heartbeats", () => {
    const { messages, rest } = parseSseBuffer(
      [
        ": connected",
        "",
        "event: alert.created",
        'data: {"alert_id":"a1","case_id":"c1","level":"MEDIO","version":1,"created_at":"2026-07-22T12:00:00+00:00"}',
        "",
        ": ping",
        "",
        "event: alert.updated",
        'data: {"alert_id":"a2","case_id":"c1","level":"BAIXO","version":2,"created_at":"2026-07-22T12:01:00+00:00"}',
        "",
        "event: alert.created",
        'data: {"alert_id":"a3"',
      ].join("\n"),
    );

    expect(messages).toHaveLength(2);
    expect(messages[0]).toEqual({
      event: "alert.created",
      data: {
        alertId: "a1",
        caseId: "c1",
        level: "MEDIO",
        version: 1,
        createdAt: "2026-07-22T12:00:00+00:00",
      },
    });
    expect(messages[1].event).toBe("alert.updated");
    expect(messages[1].data.version).toBe(2);
    expect(rest).toContain("event: alert.created");
    expect(rest).toContain('"alert_id":"a3"');
  });

  it("backoff de reconexão cresce e limita", () => {
    expect(nextReconnectDelayMs(0)).toBe(500);
    expect(nextReconnectDelayMs(1)).toBe(1000);
    expect(nextReconnectDelayMs(2)).toBe(2000);
    expect(nextReconnectDelayMs(10)).toBe(8000);
  });

  it("connectAlertsStream chama fetch com Bearer e path limpo", async () => {
    const { connectAlertsStream } = await import("@/lib/alerts/sse");
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(null, { status: 200 }),
    );
    await connectAlertsStream({
      accessToken: "tok-xyz",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/alerts/stream");
    expect(url).not.toContain("?");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer tok-xyz");
  });
});
