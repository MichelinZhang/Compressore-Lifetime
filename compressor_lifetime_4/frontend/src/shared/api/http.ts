import { del, get, post, put } from "./client";

export async function getJson<T>(path: string): Promise<T> {
  return get<T>(path);
}

export async function postJson<T>(path: string, body?: unknown): Promise<T> {
  return post<T>(path, body);
}

export async function putJson<T>(path: string, body: unknown): Promise<T> {
  return put<T>(path, body);
}

export async function deleteJson<T>(path: string): Promise<T> {
  return del<T>(path);
}
