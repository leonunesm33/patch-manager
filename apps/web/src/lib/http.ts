const API_BASE = import.meta.env.VITE_API_BASE_URL?.trim() || "/api/v1";
const AUTH_TOKEN_KEY = "patch-manager-token";

async function fetchWithAuth(path: string, init?: RequestInit): Promise<Response> {
  const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
  try {
    return await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Nao foi possivel conectar com a API. Verifique se o backend esta ativo em http://localhost:8000 e se o frontend foi iniciado pelo Vite.",
      );
    }
    throw error;
  }
}

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithAuth(path, init);

  if (!response.ok) {
    let detailMessage: string | null = null;

    try {
      const data = (await response.clone().json()) as { detail?: string };
      if (typeof data.detail === "string" && data.detail.trim()) {
        detailMessage = data.detail.trim();
      }
    } catch {
      detailMessage = null;
    }

    if (response.status === 401) {
      throw new Error(detailMessage || "Sessao expirada ou acesso nao autorizado.");
    }

    throw new Error(detailMessage || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/**
 * Like `http`, but returns the raw Response for streaming / binary downloads.
 * Caller is responsible for reading the body (e.g. response.blob()).
 */
export async function httpRaw(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetchWithAuth(path, init);

  if (!response.ok) {
    let detailMessage: string | null = null;
    try {
      const data = (await response.clone().json()) as { detail?: string };
      if (typeof data.detail === "string" && data.detail.trim()) {
        detailMessage = data.detail.trim();
      }
    } catch {
      detailMessage = null;
    }

    if (response.status === 401) {
      throw new Error(detailMessage || "Sessao expirada ou acesso nao autorizado.");
    }

    throw new Error(detailMessage || `Request failed with status ${response.status}`);
  }

  return response;
}
