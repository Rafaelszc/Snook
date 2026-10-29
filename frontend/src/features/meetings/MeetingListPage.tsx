import { Mic, Plus } from "lucide-react"
import { Link } from "react-router"

import { EmptyState } from "@/components/surfaces/EmptyState"
import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"
import { StatusBadge } from "@/components/surfaces/StatusBadge"
import { Button } from "@/components/ui/button"

import type { MeetingSummary } from "./api"
import { formatDate, formatDuration } from "./format"
import { MESSAGES } from "./messages"
import { useMeetings } from "./useMeetings"

function MeetingRow({ meeting }: { meeting: MeetingSummary }) {
  return (
    <li className="relative flex flex-col gap-2 py-4 hover:bg-sunken sm:flex-row sm:items-center sm:gap-6">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <Link
          to={`/meetings/${meeting.id}`}
          className="truncate font-heading text-base font-semibold text-ink outline-none after:absolute after:inset-0 hover:underline focus-visible:underline focus-visible:after:ring-2 focus-visible:after:ring-ring"
        >
          {meeting.title}
        </Link>
        <span className="font-mono text-sm text-ink-muted tabular-nums">
          {formatDate(meeting.created_at)} ·{" "}
          {formatDuration(meeting.duration_seconds)}
        </span>
      </div>
      <StatusBadge
        status={meeting.status}
        className="motion-fade-in self-start sm:self-auto"
      />
    </li>
  )
}

function Body() {
  const { data, error, isPending } = useMeetings()
  if (error)
    return (
      <Notice variant="error">{error.message || MESSAGES.loadError}</Notice>
    )
  if (isPending)
    return (
      <SkeletonGroup label={MESSAGES.loading}>
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </SkeletonGroup>
    )
  if (data.length === 0)
    return (
      <EmptyState title={MESSAGES.empty} description={MESSAGES.emptyHint} />
    )
  // Régua forte em --ink no topo; linhas por régua --hairline, sem card (ADR-0024).
  return (
    <ul className="divide-y divide-hairline border-t border-b border-t-ink border-b-hairline">
      {data.map((meeting) => (
        <MeetingRow key={meeting.id} meeting={meeting} />
      ))}
    </ul>
  )
}

// Tamanhos de texto: sm, base, 2xl. Um accent: "Nova reunião", que avança o fluxo.
export function MeetingListPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title={MESSAGES.listTitle}
        description={MESSAGES.listDescription}
        actions={
          <>
            <Button variant="secondary" asChild>
              <Link to="/meetings/record">
                <Mic aria-hidden="true" />
                {MESSAGES.recordMeeting}
              </Link>
            </Button>
            <Button variant="accent" asChild>
              <Link to="/meetings/new">
                <Plus aria-hidden="true" />
                {MESSAGES.newMeeting}
              </Link>
            </Button>
          </>
        }
      />
      <Body />
    </div>
  )
}
