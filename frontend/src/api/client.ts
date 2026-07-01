// Thin API client. All calls go through the Vite dev-server proxy at /api.
const BASE = "/api";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} -> HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST ${path} -> HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}
