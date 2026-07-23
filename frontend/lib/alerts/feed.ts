import { createStore } from "zustand/vanilla";
import { create } from "zustand";

import type { AlertSseMessage, AlertSsePayload } from "@/lib/alerts/sse";

export const ALERTS_REGION_ID = "regiao-alertas";
export const ALERTS_REGION_HEADING_ID = "alertas-heading";

export type AlertFeedItem = {
  key: string;
  event: string;
  data: AlertSsePayload;
  receivedAt: string;
};

export type AlertToast = {
  text: string;
  nonce: number;
};

export type AlertsFeedState = {
  connected: boolean;
  items: AlertFeedItem[];
  toast: AlertToast | null;
  setConnected: (connected: boolean) => void;
  pushEvent: (message: AlertSseMessage) => void;
};

const MAX_FEED_ITEMS = 50;

export function formatAlertToastAnnouncement(message: AlertSseMessage): string {
  const { level, version, caseId } = message.data;
  if (message.event === "alert.updated") {
    return `Alerta atualizado ${level}, versão ${version}, Caso ${caseId}.`;
  }
  return `Novo Alerta ${level}, versão ${version}, Caso ${caseId}.`;
}

function feedActions(
  set: (
    partial:
      | Partial<AlertsFeedState>
      | ((state: AlertsFeedState) => Partial<AlertsFeedState>),
  ) => void,
): Pick<AlertsFeedState, "setConnected" | "pushEvent"> {
  return {
    setConnected: (connected) => set({ connected }),
    pushEvent: (message) =>
      set((state) => {
        const item: AlertFeedItem = {
          key: `${message.data.alertId}:${message.data.version}:${state.toast ? state.toast.nonce + 1 : 1}`,
          event: message.event,
          data: message.data,
          receivedAt: new Date().toISOString(),
        };
        const nonce = (state.toast?.nonce ?? 0) + 1;
        return {
          items: [item, ...state.items].slice(0, MAX_FEED_ITEMS),
          toast: {
            text: formatAlertToastAnnouncement(message),
            nonce,
          },
        };
      }),
  };
}

/** Store sem singleton — para testes unitários. */
export function createAlertsFeedStore() {
  return createStore<AlertsFeedState>()((set) => ({
    connected: false,
    items: [],
    toast: null,
    ...feedActions(set),
  }));
}

/**
 * Feed efêmero de eventos SSE na sessão (UI).
 * Não substitui Alertas persistidos no GET do Caso (ADR 0025).
 */
export const useAlertsFeedStore = create<AlertsFeedState>()((set) => ({
  connected: false,
  items: [],
  toast: null,
  ...feedActions(set),
}));
