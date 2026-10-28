import { useVirtualizer } from "@tanstack/react-virtual"
import { useEffect, useRef, useState } from "react"

import type { SplitSegment } from "./api"
import { CutButton } from "./CutControls"
import { formatTimestamp } from "./format"
import { MESSAGES } from "./messages"

const ROW_ESTIMATE_PX = 112
const OVERSCAN = 8

interface SegmentListProps {
  segments: SplitSegment[]
  cuts: readonly number[]
  disabled?: boolean
  onToggle: (position: number) => void
  onMove: (from: number, to: number) => boolean
}

// Só os segmentos perto da área visível ficam no DOM (NFR-07).
export function SegmentList({
  segments,
  cuts,
  disabled,
  onToggle,
  onMove,
}: SegmentListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [focusCut, setFocusCut] = useState<number | null>(null)
  // eslint-disable-next-line react-hooks/incompatible-library -- sem memoização própria aqui
  const virtualizer = useVirtualizer({
    count: segments.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_ESTIMATE_PX,
    overscan: OVERSCAN,
  })

  // Corte de posição `i` na lista fecha a Parte `i + 1`.
  const partEndingAt = new Map(cuts.map((position, i) => [position, i + 1]))

  // Foco segue o corte movido, mesmo que a linha nova ainda não esteja no DOM.
  useEffect(() => {
    if (focusCut === null) return
    let frame = 0
    let tries = 0
    const focus = () => {
      const button = scrollRef.current?.querySelector<HTMLButtonElement>(
        `[data-cut="${focusCut}"]`
      )
      if (button) {
        button.focus()
        setFocusCut(null)
      } else if (tries++ < 10) frame = requestAnimationFrame(focus)
    }
    focus()
    return () => cancelAnimationFrame(frame)
  }, [focusCut, cuts])

  function move(from: number, to: number) {
    if (!onMove(from, to)) return
    virtualizer.scrollToIndex(to, { align: "auto" })
    setFocusCut(to)
  }

  return (
    <div
      ref={scrollRef}
      role="region"
      aria-label={MESSAGES.segmentsLabel}
      // Região rolável precisa ser alcançável pelo teclado.
      tabIndex={0}
      className="h-[60vh] min-h-80 overflow-auto rounded-xl border border-border"
    >
      <ol
        className="relative w-full"
        style={{ height: virtualizer.getTotalSize() }}
      >
        {virtualizer.getVirtualItems().map((item) => {
          const segment = segments[item.index]
          const isLast = item.index === segments.length - 1
          return (
            <li
              key={segment.id}
              ref={virtualizer.measureElement}
              data-index={item.index}
              className="absolute inset-x-0 top-0"
              style={{ transform: `translateY(${item.start}px)` }}
            >
              <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 px-4 pt-3 pb-1 text-sm">
                <span className="font-mono text-muted-foreground tabular-nums">
                  {formatTimestamp(segment.start_seconds)}
                </span>
                <span className="font-medium">{segment.participant}</span>
                <p className="col-start-2 text-base">{segment.text}</p>
              </div>
              {isLast ? (
                <div className="h-3" />
              ) : (
                <CutButton
                  position={item.index}
                  partIndex={partEndingAt.get(item.index) ?? null}
                  endSeconds={segment.end_seconds}
                  disabled={disabled}
                  onToggle={onToggle}
                  onMove={move}
                />
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
