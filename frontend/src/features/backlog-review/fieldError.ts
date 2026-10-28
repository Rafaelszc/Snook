import { isApiError } from "@/lib/api/errors"

// Erro da API junto ao campo (`backlog-review` 40): `fields[field]` ou a mensagem geral.
export function fieldError(error: unknown, field: string): string {
  if (!isApiError(error)) return "Erro inesperado."
  return error.fields[field] ?? error.message
}
