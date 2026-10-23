import { Plus } from "lucide-react"
import { Link } from "react-router"

import { StatusBadge } from "@/components/surfaces/StatusBadge"
import { Button } from "@/components/ui/button"

import type { MeetingSummary } from "./api"
import { formatDate, formatDuration } from "./format"
import { MESSAGES } from "./messages"
import { useMeetings } from "./useMeetings"

function MeetingRow({ meeting }: { meeting: MeetingSummary }) {
  return (
    <li className="relative flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:gap-6">
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <Link
          to={`/meetings/${meeting.id}`}
          className="truncate text-base font-medium after:absolute after:inset-0 hover:underline focus-visible:underline"
        >
          {meeting.title}
        </Link>
        <span className="font-mono text-sm text-muted-foreground tabular-nums">
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
      <p
        role="alert"
        className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
      >
        {error.message || MESSAGES.loadError}
      </p>
    )
  if (isPending)
    return (
      <div aria-busy="true" className="flex flex-col gap-3">
        <span role="status" className="sr-only">
          {MESSAGES.loading}
        </span>
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className="h-16 rounded-lg bg-muted" />
        ))}
      </div>
    )
  if (data.length === 0)
    return (
      <div className="flex flex-col items-start gap-1 rounded-xl border border-dashed border-border px-5 py-10">
        <p className="text-base font-medium">{MESSAGES.empty}</p>
        <p className="text-sm text-muted-foreground">{MESSAGES.emptyHint}</p>
      </div>
    )
  return (
    <ul className="divide-y divide-border border-y border-border">
      {data.map((meeting) => (
        <MeetingRow key={meeting.id} meeting={meeting} />
      ))}
    </ul>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function MeetingListPage() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 py-4">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold text-balance">
            {MESSAGES.listTitle}
          </h1>
          <p className="text-sm text-muted-foreground">
            {MESSAGES.listDescription}
          </p>
        </div>
        <Button asChild>
          <Link to="/meetings/new">
            <Plus aria-hidden="true" />
            {MESSAGES.newMeeting}
          </Link>
        </Button>
      </header>
      <Body />
    </div>
  )
}
