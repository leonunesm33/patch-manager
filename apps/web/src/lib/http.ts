const API_BASE = "http://localhost:8000/api/v1";
const AUTH_TOKEN_KEY = "patch-manager-token";

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Sessao expirada ou acesso nao autorizado.");
    }

    throw new Error(`Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
