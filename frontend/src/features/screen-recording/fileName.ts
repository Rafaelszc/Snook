const pad = (n: number) => String(n).padStart(2, "0")

// `gravacao-AAAA-MM-DD-HHhMM.webm`, hora local do início (`screen-recording` 14).
export function recordingFileName(startedAt: number): string {
  const d = new Date(startedAt)
  const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  return `gravacao-${date}-${pad(d.getHours())}h${pad(d.getMinutes())}.webm`
}
