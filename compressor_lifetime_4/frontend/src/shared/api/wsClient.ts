import { WS_EVENTS_URL } from "../config/env";
import type { EventEnvelope } from "../types/contracts";

export type EventSocketHandle = {
  close: () => void;
};

type Options = {
  reconnectMs?: number;
  maxReconnectAttempts?: number;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: () => void;
  onUnavailable?: () => void;
};

export function createEventSocket(onEvent: (event: EventEnvelope) => void, options: Options = {}): EventSocketHandle {
  const reconnectMs = options.reconnectMs ?? 1200;
  const maxReconnectAttempts = options.maxReconnectAttempts ?? 8;
  let ws: WebSocket | null = null;
  let manuallyClosed = false;
  let reconnectTimer: number | null = null;
  let reconnectAttempts = 0;
  let unavailableNotified = false;

  const scheduleReconnect = () => {
    if (manuallyClosed) {
      return;
    }
    reconnectAttempts += 1;
    if (reconnectAttempts > maxReconnectAttempts) {
      if (!unavailableNotified) {
        unavailableNotified = true;
        options.onUnavailable?.();
      }
      return;
    }
    reconnectTimer = window.setTimeout(connect, reconnectMs);
  };

  const connect = () => {
    try {
      ws = new WebSocket(WS_EVENTS_URL);
    } catch {
      options.onError?.();
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      reconnectAttempts = 0;
      unavailableNotified = false;
      options.onOpen?.();
    };
    ws.onmessage = (msg) => {
      try {
        onEvent(JSON.parse(msg.data) as EventEnvelope);
      } catch {
        // Ignore malformed payloads.
      }
    };
    ws.onerror = () => {
      options.onError?.();
    };
    ws.onclose = () => {
      options.onClose?.();
      scheduleReconnect();
    };
  };

  connect();

  return {
    close: () => {
      manuallyClosed = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    },
  };
}
