/** TDD T7.7 — toast polite + feed de Alertas navegável. */

import { describe, expect, it } from "vitest";

import {
  ALERTS_REGION_HEADING_ID,
  ALERTS_REGION_ID,
  createAlertsFeedStore,
  formatAlertToastAnnouncement,
} from "@/lib/alerts/feed";
import type { AlertSseMessage } from "@/lib/alerts/sse";
import { primaryNavItems } from "@/lib/shell/nav";

const sampleCreated: AlertSseMessage = {
  event: "alert.created",
  data: {
    alertId: "a1",
    caseId: "c1",
    level: "MEDIO",
    version: 1,
    createdAt: "2026-07-22T12:00:00+00:00",
  },
};

const sampleUpdated: AlertSseMessage = {
  event: "alert.updated",
  data: {
    alertId: "a2",
    caseId: "c1",
    level: "ALTO",
    version: 2,
    createdAt: "2026-07-22T12:01:00+00:00",
  },
};

describe("alerts toast announcement (T7.7)", () => {
  it("formata anúncio polite para alert.created e alert.updated", () => {
    expect(formatAlertToastAnnouncement(sampleCreated)).toBe(
      "Novo Alerta MEDIO, versão 1, Caso c1.",
    );
    expect(formatAlertToastAnnouncement(sampleUpdated)).toBe(
      "Alerta atualizado ALTO, versão 2, Caso c1.",
    );
  });
});

describe("alerts feed store (T7.7)", () => {
  it("começa vazio e desconectado", () => {
    const store = createAlertsFeedStore();
    expect(store.getState().items).toEqual([]);
    expect(store.getState().connected).toBe(false);
    expect(store.getState().toast).toBeNull();
  });

  it("pushEvent acumula itens e atualiza toast com nonce", () => {
    const store = createAlertsFeedStore();
    store.getState().pushEvent(sampleCreated);
    store.getState().pushEvent(sampleUpdated);

    const state = store.getState();
    expect(state.items).toHaveLength(2);
    expect(state.items[0].event).toBe("alert.updated");
    expect(state.items[0].data.alertId).toBe("a2");
    expect(state.items[1].data.alertId).toBe("a1");
    expect(state.toast?.text).toContain("Alerta atualizado ALTO");
    expect(state.toast?.nonce).toBe(2);
  });

  it("expõe ids estáveis da região navegável", () => {
    expect(ALERTS_REGION_ID).toBe("regiao-alertas");
    expect(ALERTS_REGION_HEADING_ID).toBe("alertas-heading");
  });
});

describe("shell nav Alertas (T7.7)", () => {
  it("habilita a rota /alertas no shell", () => {
    const alertas = primaryNavItems.find((item) => item.href === "/alertas");
    expect(alertas?.enabled).toBe(true);
    expect(alertas?.label).toBe("Alertas");
  });
});
