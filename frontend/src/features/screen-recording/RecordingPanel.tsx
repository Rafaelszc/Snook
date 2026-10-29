import { Square } from "lucide-react"

import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { Button } from "@/components/ui/button"

import type { Clock } from "./capture/interfaces"
import { MESSAGES } from "./messages"
import { RecordingIndicator } from "./RecordingIndicator"
import { formatElapsed, useElapsed } from "./useElapsed"

// Único vidro do app: painel flutuante da gravação (ADR-0024, "Vidro"). Tamanhos de texto: sm, 2xl.
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
      className="motion-enter fixed inset-x-4 bottom-4 z-40 mx-auto flex max-w-md items-center gap-4 rounded-lg p-4"
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p
          role="status"
          className="flex items-center gap-2 text-sm font-medium text-ink"
        >
          <RecordingIndicator />
          {MESSAGES.recording}
        </p>
        <p
          role="timer"
          aria-label={MESSAGES.elapsed}
          className="font-mono text-2xl font-semibold text-ink tabular-nums"
        >
          {formatElapsed(elapsed)}
        </p>
      </div>
      <Button variant="danger" disabled={stopping} onClick={onStop}>
        <Square aria-hidden="true" />
        {stopping ? MESSAGES.stopping : MESSAGES.stop}
      </Button>
    </GlassPanel>
  )
}
