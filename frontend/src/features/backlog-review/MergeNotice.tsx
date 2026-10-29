import { Notice } from "@/components/surfaces/Notice"

// Aviso de junção antes de salvar (`backlog-review` 41).
export function MergeNotice({ id, message }: { id: string; message?: string }) {
  if (!message) return null
  return (
    <Notice id={id} variant="info">
      {message}
    </Notice>
  )
}
