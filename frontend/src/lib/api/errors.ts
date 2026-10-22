// 05-api.md, "Erros": {"error": {"code", "message", "fields"}}.
export type FieldErrors = Record<string, string>

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: FieldErrors

  constructor(
    status: number,
    code: string,
    message: string,
    fields: FieldErrors = {}
  ) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let body: unknown
  try {
    body = await response.json()
  } catch {
    body = null
  }
  const error = (body as { error?: Record<string, unknown> } | null)?.error
  if (error && typeof error.code === "string") {
    const fields =
      error.fields && typeof error.fields === "object"
        ? (error.fields as FieldErrors)
        : {}
    return new ApiError(
      response.status,
      error.code,
      typeof error.message === "string" ? error.message : "Erro inesperado.",
      fields
    )
  }
  return new ApiError(response.status, "unknown_error", "Erro inesperado.")
}
