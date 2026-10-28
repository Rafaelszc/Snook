import { ArrowLeft, CircleAlert } from "lucide-react"
import { Link, useParams } from "react-router"

import { StatusBadge } from "@/components/surfaces/StatusBadge"
import { buttonVariants } from "@/components/ui/button"

import type { MeetingDetail } from "./api"
import { DeleteMeetingDialog } from "./DeleteMeetingDialog"
import { formatDate, formatDuration } from "./format"
import { MESSAGES, STAGE_LABELS } from "./messages"
import { RetryButton } from "./RetryButton"
import { TitleEditor } from "./TitleEditor"
import { useMeeting } from "./useMeetings"

function Facts({ meeting }: { meeting: MeetingDetail }) {
  const rows = [
    {
      term: MESSAGES.createdAt,
      value: formatDate(meeting.created_at),
      mono: true,
    },
    {
      term: MESSAGES.duration,
      value: formatDuration(meeting.duration_seconds),
      mono: true,
    },
    { term: MESSAGES.originalFilename, value: meeting.original_filename },
    {
      term: MESSAGES.expectedSpeakers,
      value: meeting.expected_speakers?.toString() ?? MESSAGES.notSet,
      mono: true,
    },
  ]
  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2 text-sm">
      {rows.map(({ term, value, mono }) => (
        <div key={term} className="contents">
          <dt className="text-muted-foreground">{term}</dt>
          <dd
            title={value}
            className={mono ? "truncate font-mono tabular-nums" : "truncate"}
          >
            {value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function Failure({ meeting }: { meeting: MeetingDetail }) {
  if (meeting.status !== "failed") return null
  return (
    <section className="flex flex-col gap-4 rounded-xl border border-destructive/40 p-5">
      <div className="flex items-start gap-2 text-sm">
        <CircleAlert
          aria-hidden="true"
          className="mt-0.5 size-4 shrink-0 text-destructive"
        />
        <div className="flex flex-col gap-1">
          {meeting.failed_stage ? (
            <p className="font-medium">
              {MESSAGES.failedAt(STAGE_LABELS[meeting.failed_stage])}
            </p>
          ) : null}
          <p className="text-muted-foreground">{meeting.error_message}</p>
        </div>
      </div>
      <RetryButton meeting={meeting} />
    </section>
  )
}

// Transcrita sem nomes: o próximo passo é a tela de nomeação (`participants` 25).
function NamingCall({ meeting }: { meeting: MeetingDetail }) {
  if (meeting.status !== "transcribed" || meeting.participants_confirmed)
    return null
  return (
    <section className="flex flex-col items-start gap-3 rounded-xl border border-border p-5">
      <p className="text-sm text-muted-foreground">
        {MESSAGES.nameParticipantsHint}
      </p>
      <Link
        to={`/meetings/${meeting.id}/participants`}
        className={buttonVariants()}
      >
        {MESSAGES.nameParticipants}
      </Link>
    </section>
  )
}

// Não cabe no modelo: o próximo passo é a tela de divisão (`transcript-split` 30).
function SplitCall({ meeting }: { meeting: MeetingDetail }) {
  if (meeting.status !== "needs_split") return null
  return (
    <section className="flex flex-col items-start gap-3 rounded-xl border border-border p-5">
      <p className="text-sm text-muted-foreground">
        {MESSAGES.splitMeetingHint}
      </p>
      <Link to={`/meetings/${meeting.id}/split`} className={buttonVariants()}>
        {MESSAGES.splitMeeting}
      </Link>
    </section>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function MeetingDetailPage() {
  const { id = "" } = useParams()
  const { data: meeting, error, isPending } = useMeeting(id)
  const hasTranscript =
    meeting !== undefined &&
    !["pending", "processing"].includes(meeting.status) &&
    !(meeting.status === "failed" && meeting.failed_stage === "transcription")

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 py-4">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      {error ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {error.status === 404 ? MESSAGES.notFound : error.message}
        </p>
      ) : isPending ? (
        <div aria-busy="true" className="flex flex-col gap-4">
          <span role="status" className="sr-only">
            {MESSAGES.loading}
          </span>
          <div className="h-9 w-2/3 rounded-lg bg-muted" />
          <div className="h-32 rounded-xl bg-muted" />
        </div>
      ) : (
        <>
          <header className="flex flex-col gap-3">
            <TitleEditor
              key={meeting.title}
              id={meeting.id}
              title={meeting.title}
            />
            <StatusBadge status={meeting.status} className="self-start" />
          </header>
          <Failure meeting={meeting} />
          <NamingCall meeting={meeting} />
          <SplitCall meeting={meeting} />
          <Facts meeting={meeting} />
          {meeting.has_backlog ? (
            <Link
              to={`/meetings/${meeting.id}/backlog`}
              className={`${buttonVariants()} self-start`}
            >
              {MESSAGES.openBacklog}
            </Link>
          ) : null}
          {hasTranscript ? (
            <Link
              to={`/meetings/${meeting.id}/transcript`}
              className="self-start text-sm font-medium underline underline-offset-4"
            >
              {MESSAGES.openTranscript}
            </Link>
          ) : null}
          <div className="border-t border-border pt-5">
            <DeleteMeetingDialog meetingId={meeting.id} />
          </div>
        </>
      )}
    </div>
  )
}
