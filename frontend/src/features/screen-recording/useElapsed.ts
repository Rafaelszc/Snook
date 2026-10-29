import { useEffect, useState } from "react"

import type { Clock } from "./capture/interfaces"

// Meio segundo evita pular um segundo na tela quando o timer atrasa.
const TICK_MS = 500

export function useElapsed(startedAt: number, clock: Clock): number {
  const [now, setNow] = useState(() => clock.now())
  useEffect(() => {
    const id = setInterval(() => setNow(clock.now()), TICK_MS)
    return () => clearInterval(id)
  }, [clock])
  return Math.max(0, Math.floor((now - startedAt) / 1000))
}

// H:MM:SS.
export function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}
