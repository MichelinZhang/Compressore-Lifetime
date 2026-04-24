import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createEventSocket } from "./wsClient";

type MessageLike = { data: string };

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  onopen: ((ev: Event) => unknown) | null = null;
  onmessage: ((ev: MessageLike) => unknown) | null = null;
  onerror: ((ev: Event) => unknown) | null = null;
  onclose: ((ev: CloseEvent) => unknown) | null = null;

  url: string;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
    this.onclose?.({} as CloseEvent);
  }

  emitOpen() {
    this.onopen?.({} as Event);
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  emitClose() {
    this.onclose?.({} as CloseEvent);
  }
}

describe("createEventSocket", () => {
  const originalWebSocket = window.WebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    FakeWebSocket.instances = [];
    Object.defineProperty(window, "WebSocket", {
      writable: true,
      configurable: true,
      value: FakeWebSocket,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    Object.defineProperty(window, "WebSocket", {
      writable: true,
      configurable: true,
      value: originalWebSocket,
    });
  });

  it("parses incoming event payload", () => {
    const onEvent = vi.fn();
    const handle = createEventSocket(onEvent);
    const ws = FakeWebSocket.instances[0];
    ws.emitMessage({ event: "station.status", stationId: 1, ts: Date.now(), payload: { status: "running" } });

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent.mock.calls[0][0].event).toBe("station.status");

    handle.close();
  });

  it("stops reconnecting after max attempts and marks unavailable", () => {
    const onUnavailable = vi.fn();
    const handle = createEventSocket(() => undefined, {
      reconnectMs: 10,
      maxReconnectAttempts: 2,
      onUnavailable,
    });

    FakeWebSocket.instances[0].emitClose();
    vi.advanceTimersByTime(10);
    FakeWebSocket.instances[1].emitClose();
    vi.advanceTimersByTime(10);
    FakeWebSocket.instances[2].emitClose();

    expect(onUnavailable).toHaveBeenCalledTimes(1);
    expect(FakeWebSocket.instances.length).toBe(3);

    handle.close();
  });

  it("resets retry budget after successful reconnect", () => {
    const onUnavailable = vi.fn();
    const handle = createEventSocket(() => undefined, {
      reconnectMs: 10,
      maxReconnectAttempts: 1,
      onUnavailable,
    });

    FakeWebSocket.instances[0].emitClose();
    vi.advanceTimersByTime(10);
    FakeWebSocket.instances[1].emitOpen();
    FakeWebSocket.instances[1].emitClose();
    vi.advanceTimersByTime(10);

    expect(onUnavailable).not.toHaveBeenCalled();
    expect(FakeWebSocket.instances.length).toBe(3);

    handle.close();
  });
});

