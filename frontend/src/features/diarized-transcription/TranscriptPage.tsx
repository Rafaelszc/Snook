import { useVirtualizer } from "@tanstack/react-virtual"
import { ArrowLeft } from "lucide-react"
import { useRef } from "react"
import { Link, useParams } from "react-router"

import { StatusBadge } from "@/components/surfaces/StatusBadge"

import { hasTranscript, type TranscriptSegment } from "./api"
import { formatTimestamp } from "./format"
import { MESSAGES } from "./messages"
import { useMeetingStatus, useTranscript } from "./useTranscript"

const ROW_ESTIMATE_PX = 72
const OVERSCAN = 8

function SegmentList({ segments }: { segments: TranscriptSegment[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line react-hooks/incompatible-library -- sem memoização própria aqui
  const virtualizer = useVirtualizer({
    count: segments.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_ESTIMATE_PX,
    overscan: OVERSCAN,
  })

  return (
    <div
      ref={scrollRef}
      role="region"
      aria-label={MESSAGES.segmentsLabel}
      // Região rolável precisa ser alcançável pelo teclado.
      tabIndex={0}
      className="h-[70vh] overflow-auto rounded-xl border border-border"
    >
      <ol
        className="relative w-full"
        style={{ height: virtualizer.getTotalSize() }}
      >
        {virtualizer.getVirtualItems().map((item) => {
          const segment = segments[item.index]
          return (
            <li
              key={segment.id}
              ref={virtualizer.measureElement}
              data-index={item.index}
              className="absolute inset-x-0 top-0 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 border-b border-border px-4 py-3 text-sm"
              style={{ transform: `translateY(${item.start}px)` }}
            >
              <span className="font-mono text-muted-foreground tabular-nums">
                {formatTimestamp(segment.start_seconds)}
              </span>
              <span className="font-medium">{segment.speaker_label}</span>
              <p className="col-start-2 text-base">{segment.text}</p>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function TranscriptPage() {
  const { id = "" } = useParams()
  const { data: meeting, error: meetingError } = useMeetingStatus(id)
  const ready = meeting !== undefined && hasTranscript(meeting)
  const { data: transcript, error: transcriptError } = useTranscript(id, ready)
  const error = meetingError ?? transcriptError

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 py-4">
      <Link
        to={`/meetings/${id}`}
        className="inline-flex items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <h1 className="text-2xl font-semibold">{MESSAGES.title}</h1>
      {error ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {error.status === 404 ? MESSAGES.notFound : error.message}
        </p>
      ) : meeting && !ready ? (
        <div className="flex flex-col gap-3">
          <StatusBadge status={meeting.status} className="self-start" />
          <p className="text-sm text-muted-foreground">{MESSAGES.notReady}</p>
        </div>
      ) : !transcript ? (
        <div aria-busy="true">
          <span role="status" className="sr-only">
            {MESSAGES.loading}
          </span>
          <div className="h-32 rounded-xl bg-muted" />
        </div>
      ) : transcript.segments.length === 0 ? (
        <p className="text-sm text-muted-foreground">{MESSAGES.empty}</p>
      ) : (
        <SegmentList segments={transcript.segments} />
      )}
    </div>
  )
}
