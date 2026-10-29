import { useVirtualizer } from "@tanstack/react-virtual"
import { ArrowLeft } from "lucide-react"
import { useRef } from "react"
import { Link, useParams } from "react-router"

import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"
import { StatusBadge } from "@/components/surfaces/StatusBadge"

import { hasTranscript, type TranscriptSegment } from "./api"
import { formatTimestamp } from "./format"
import { MESSAGES } from "./messages"
import { useParticipantNames } from "./useParticipantNames"
import { useMeetingStatus, useTranscript } from "./useTranscript"

const ROW_ESTIMATE_PX = 72
const OVERSCAN = 8

function SegmentList({
  segments,
  names,
}: {
  segments: TranscriptSegment[]
  names: ReadonlyMap<string, string>
}) {
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
      className="h-[70vh] overflow-auto border-y border-hairline outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
              className="absolute inset-x-0 top-0 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 border-b border-hairline py-3 text-sm"
              style={{ transform: `translateY(${item.start}px)` }}
            >
              <span className="font-mono text-ink-muted tabular-nums">
                {formatTimestamp(segment.start_seconds)}
              </span>
              <span className="font-sans font-medium text-ink">
                {names.get(segment.speaker_label) ?? segment.speaker_label}
              </span>
              <p className="col-start-2 font-serif text-base text-pretty text-ink">
                {segment.text}
              </p>
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
  const names = useParticipantNames(id, ready)
  const error = meetingError ?? transcriptError

  return (
    <div className="flex w-full max-w-reading flex-col gap-6">
      <Link
        to={`/meetings/${id}`}
        className="inline-flex items-center gap-2 self-start rounded-sm text-sm text-ink-muted outline-none hover:text-ink focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <PageHeader title={MESSAGES.title} />
      {error ? (
        <Notice variant="error">
          {error.status === 404 ? MESSAGES.notFound : error.message}
        </Notice>
      ) : meeting && !ready ? (
        <div className="flex flex-col gap-3">
          <StatusBadge status={meeting.status} className="self-start" />
          <p className="text-sm text-ink-muted">{MESSAGES.notReady}</p>
        </div>
      ) : !transcript ? (
        <SkeletonGroup label={MESSAGES.loading}>
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </SkeletonGroup>
      ) : transcript.segments.length === 0 ? (
        <p className="text-sm text-ink-muted">{MESSAGES.empty}</p>
      ) : (
        <SegmentList segments={transcript.segments} names={names} />
      )}
    </div>
  )
}
