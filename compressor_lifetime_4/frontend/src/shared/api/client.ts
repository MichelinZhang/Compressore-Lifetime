import { API_BASE_URL } from "../config/env";
import { ApiError } from "../utils/errors";

type RequestOptions = RequestInit & {
  timeoutMs?: number;
};

function resolveUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalized}`;
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 12000, headers, ...rest } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(resolveUrl(path), {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      signal: controller.signal,
    });
    const body = await parseBody(res);
    if (!res.ok) {
      const detail =
        typeof body === "string"
          ? body
          : typeof body === "object" && body && "detail" in body
            ? String((body as Record<string, unknown>).detail)
            : `HTTP ${res.status}`;
      throw new ApiError(res.status, detail, body);
    }
    return body as T;
  } finally {
    clearTimeout(timer);
  }
}

export async function get<T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
  return request<T>(path, { ...options, method: "GET" });
}

export async function post<T>(path: string, body?: unknown, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
  return request<T>(path, {
    ...options,
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function put<T>(path: string, body: unknown, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
  return request<T>(path, {
    ...options,
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function del<T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
  return request<T>(path, { ...options, method: "DELETE" });
}

