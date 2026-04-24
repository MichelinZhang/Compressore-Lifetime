const FALLBACK_API_BASE = typeof window !== "undefined" ? window.location.origin : "";

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function apiToWsBase(apiBase: string): string {
  if (!apiBase) {
    if (typeof window !== "undefined") {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      return `${proto}://${window.location.host}`;
    }
    return "";
  }
  if (apiBase.startsWith("https://")) {
    return `wss://${apiBase.slice("https://".length)}`;
  }
  if (apiBase.startsWith("http://")) {
    return `ws://${apiBase.slice("http://".length)}`;
  }
  if (apiBase.startsWith("wss://") || apiBase.startsWith("ws://")) {
    return apiBase;
  }
  return `ws://${apiBase}`;
}

const configuredApiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
const configuredWsBase = (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.trim();

export const API_BASE_URL = stripTrailingSlash(configuredApiBase || FALLBACK_API_BASE);
export const WS_BASE_URL = stripTrailingSlash(configuredWsBase || apiToWsBase(API_BASE_URL));
export const WS_EVENTS_URL = `${WS_BASE_URL}/ws/events`;
