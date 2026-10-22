import { ApiError, parseApiError } from "./errors"

const API_PREFIX = "/api"

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"

interface RequestOptions {
  method?: Method
  body?: unknown
  signal?: AbortSignal
}

// Sessão vai só no cookie HttpOnly; nada de token em Web Storage (03-security.md, "Never").
export async function apiFetch<T>(
  path: string,
  { method = "GET", body, signal }: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" }
  const init: RequestInit = {
    method,
    headers,
    credentials: "same-origin",
    redirect: "error",
    signal,
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json"
    init.body = JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(`${API_PREFIX}${path}`, init)
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError")
      throw cause
    throw new ApiError(0, "network_error", "Sem conexão com o servidor.")
  }

  if (!response.ok) throw await parseApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => apiFetch<T>(path, { signal }),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body }),
  put: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
}
