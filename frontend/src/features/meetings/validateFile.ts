import { EMPTY_FILE, TOO_LARGE, UNSUPPORTED_FORMAT } from "./messages"

// Mesmas regras do servidor (ADR-0018): a API continua sendo a fonte de verdade.
export const ACCEPTED_EXTENSIONS = ["mp3", "wav", "m4a", "ogg", "webm", "mp4"]
export const MAX_UPLOAD_BYTES = 524_288_000

export function fileExtension(name: string): string {
  const dot = name.lastIndexOf(".")
  return dot < 0 ? "" : name.slice(dot + 1).toLowerCase()
}

// Devolve a mensagem de recusa, ou null se o arquivo pode ir (`meetings` 37).
export function validateFile(file: File): string | null {
  if (!ACCEPTED_EXTENSIONS.includes(fileExtension(file.name)))
    return UNSUPPORTED_FORMAT
  if (file.size > MAX_UPLOAD_BYTES) return TOO_LARGE
  if (file.size === 0) return EMPTY_FILE
  return null
}

// Mesmo padrão do servidor: título vazio vira o nome do arquivo (`meetings` 36).
export function titleFromFile(name: string): string {
  return name.slice(0, 200)
}
