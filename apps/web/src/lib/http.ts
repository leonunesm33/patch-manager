const API_BASE = import.meta.env.VITE_API_BASE_URL?.trim() || "/api/v1";
const AUTH_TOKEN_KEY = "patch-manager-token";

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
  let response: Response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
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
