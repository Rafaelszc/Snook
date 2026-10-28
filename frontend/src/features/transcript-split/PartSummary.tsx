import { CircleAlert, CircleCheck } from "lucide-react"

import { cn } from "@/lib/utils"

import type { ClientPart } from "./api"
import { MESSAGES } from "./messages"

// Intervalo, estimativa e se cabe, por Parte; refeito a cada mudança (`transcript-split` 34).
export function PartSummary({ parts }: { parts: ClientPart[] }) {
  return (
    <ol aria-label={MESSAGES.partsLabel} className="flex flex-col">
      {parts.map((part) => (
        <li
          key={part.index}
          className="grid grid-cols-[4.5rem_minmax(0,1fr)_auto] items-center gap-x-3 border-b border-border py-2 text-sm last:border-b-0"
        >
          <span className="font-medium">{MESSAGES.partName(part.index)}</span>
          <span className="flex flex-wrap gap-x-3 font-mono text-muted-foreground tabular-nums">
            <span>
              {MESSAGES.partRange(part.startSeconds, part.endSeconds)}
            </span>
            <span>{MESSAGES.partTokens(part.tokens)}</span>
          </span>
          <span
            className={cn(
              "inline-flex items-center gap-1",
              part.fits ? "text-status-done" : "text-destructive"
            )}
          >
            {part.fits ? (
              <CircleCheck aria-hidden="true" className="size-4" />
            ) : (
              <CircleAlert aria-hidden="true" className="size-4" />
            )}
            {part.fits ? MESSAGES.fits : MESSAGES.tooLarge}
          </span>
        </li>
      ))}
    </ol>
  )
}
