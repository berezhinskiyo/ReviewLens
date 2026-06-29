// HTTP-клиент с ротацией refresh-токена и device-fingerprint.
// База по умолчанию — /api (через прокси Vite / nginx); локально можно
// переопределить VITE_API_BASE_URL.
export const API_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";
const RT_KEY = "reviewlens_refresh_token";

export function getDeviceFingerprint(): string {
  const k = "reviewlens_fp_v1";
  let v = sessionStorage.getItem(k);
  if (!v) {
    const rnd =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random()}`;
    v = btoa(unescape(encodeURIComponent(rnd))).slice(0, 32);
    sessionStorage.setItem(k, v);
  }
  return v;
}

export function formatApiError(body: { detail?: unknown }): string {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((x: { msg?: string; loc?: (string | number)[] }) => {
        const path = x.loc?.filter((p) => p !== "body").join(".") ?? "";
        return path ? `${path}: ${x.msg}` : x.msg ?? JSON.stringify(x);
      })
      .join("; ");
  }
  return "Ошибка запроса";
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(RT_KEY);
}
export function setRefreshToken(token: string) {
  sessionStorage.setItem(RT_KEY, token);
}
export function clearRefreshToken() {
  sessionStorage.removeItem(RT_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const rt = getRefreshToken();
  if (!rt) return null;
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!res.ok) {
    clearRefreshToken();
    return null;
  }
  const data = await res.json();
  setRefreshToken(data.refresh_token);
  return data.access_token as string;
}

async function readBody(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch {
    return "";
  }
}

function parseErrorBody(text: string): { detail?: unknown } {
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return {};
  }
}

async function parseOk<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const text = await readBody(response);
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error("Сервер вернул некорректный ответ");
  }
}

export async function publicApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Device-Fingerprint": getDeviceFingerprint(),
    ...(options.headers as Record<string, string>),
  };
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    throw new Error(formatApiError(parseErrorBody(await readBody(response))));
  }
  return parseOk<T>(response);
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string | null,
  retried = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Device-Fingerprint": getDeviceFingerprint(),
    ...(options.headers as Record<string, string>),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (response.status === 401 && !retried && path !== "/auth/refresh") {
    const newAccess = await refreshAccessToken();
    if (newAccess) return api<T>(path, options, newAccess, true);
  }
  if (!response.ok) {
    throw new Error(formatApiError(parseErrorBody(await readBody(response))));
  }
  return parseOk<T>(response);
}
