// Aviso de junção antes de salvar (`backlog-review` 41).
export function MergeNotice({ id, message }: { id: string; message?: string }) {
  if (!message) return null
  return (
    <p id={id} role="status" className="text-sm text-signal">
      {message}
    </p>
  )
}
