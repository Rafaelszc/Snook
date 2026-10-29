import { Scissors } from "lucide-react"
import type { KeyboardEvent } from "react"

import { cn } from "@/lib/utils"

import { formatTimestamp } from "./format"
import { MESSAGES } from "./messages"

export const CUTS_HINT_ID = "split-cuts-hint"

interface CutButtonProps {
  position: number
  // Parte que termina neste corte; ausente quando não há corte.
  partIndex: number | null
  endSeconds: number
  disabled?: boolean
  onToggle: (position: number) => void
  onMove: (from: number, to: number) => void
}

// Fronteira no fim de um segmento: só aí cabe corte (`transcript-split` 33).
// Num corte, setas para cima e para baixo movem para a fala vizinha.
export function CutButton({
  position,
  partIndex,
  endSeconds,
  disabled,
  onToggle,
  onMove,
}: CutButtonProps) {
  const active = partIndex !== null

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (!active) return
    const step =
      event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0
    if (!step) return
    event.preventDefault()
    onMove(position, position + step)
  }

  // Alinha à coluna do texto da fala; o traço marca o fim da Parte.
  return (
    <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-x-4 px-4 py-1">
      <div className="col-start-2 flex items-center gap-3">
        <button
          type="button"
          data-cut={position}
          aria-pressed={active}
          aria-describedby={CUTS_HINT_ID}
          aria-keyshortcuts={active ? "ArrowUp ArrowDown" : undefined}
          disabled={disabled}
          onClick={() => onToggle(position)}
          onKeyDown={onKeyDown}
          className={cn(
            "motion-press inline-flex min-h-8 shrink-0 items-center gap-1.5 rounded-md border px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.97] disabled:opacity-50",
            active
              ? "border-signal bg-signal text-signal-ink"
              : "-ml-2.5 border-transparent text-muted-foreground hover:border-border hover:text-foreground"
          )}
        >
          <Scissors aria-hidden="true" className="size-3.5" />
          {active ? MESSAGES.cutEnd(partIndex) : MESSAGES.cutHere}{" "}
          <span className="sr-only">
            {MESSAGES.cutAfter(formatTimestamp(endSeconds))}
          </span>
        </button>
        <span
          aria-hidden="true"
          className={cn(
            "motion-fade h-px flex-1 bg-signal",
            active ? "opacity-100" : "opacity-0"
          )}
        />
      </div>
    </div>
  )
}
