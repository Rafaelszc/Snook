import { Square } from "lucide-react"

import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { Button } from "@/components/ui/button"

import type { Clock } from "./capture/interfaces"
import { MESSAGES } from "./messages"
import { RecordingIndicator } from "./RecordingIndicator"
import { formatElapsed, useElapsed } from "./useElapsed"

// Painel flutuante da gravação (ADR-0022, "Mapa de superfícies"). Tamanhos de texto: sm, 2xl.
export function RecordingPanel({
  startedAt,
  clock,
  stopping,
  onStop,
}: {
  startedAt: number
  clock: Clock
  stopping: boolean
  onStop: () => void
}) {
  const elapsed = useElapsed(startedAt, clock)
  return (
    <GlassPanel
      role="region"
      aria-label={MESSAGES.panel}
      className="motion-enter fixed inset-x-4 bottom-4 z-40 mx-auto flex max-w-md items-center gap-4 rounded-xl px-5 py-4"
    >
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p
          role="status"
          className="flex items-center gap-2 text-sm font-medium"
        >
          <RecordingIndicator />
          {MESSAGES.recording}
        </p>
        <p
          role="timer"
          aria-label={MESSAGES.elapsed}
          className="font-mono text-2xl font-semibold tabular-nums"
        >
          {formatElapsed(elapsed)}
        </p>
      </div>
      <Button variant="destructive" disabled={stopping} onClick={onStop}>
        <Square aria-hidden="true" />
        {stopping ? MESSAGES.stopping : MESSAGES.stop}
      </Button>
    </GlassPanel>
  )
}
