import { ArrowLeft } from "lucide-react"
import { Link, useParams } from "react-router"

import { Notice } from "@/components/surfaces/Notice"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"
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
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2 border-t border-hairline pt-4 text-sm">
      {rows.map(({ term, value, mono }) => (
        <div key={term} className="contents">
          <dt className="text-ink-muted">{term}</dt>
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

// Retry fora do Notice: o erro dele é outro alerta, sem aninhar regiões vivas.
function Failure({ meeting }: { meeting: MeetingDetail }) {
  if (meeting.status !== "failed") return null
  return (
    <div className="flex flex-col gap-3">
      <Notice variant="error">
        <div className="flex flex-col gap-1">
          {meeting.failed_stage ? (
            <p className="font-medium">
              {MESSAGES.failedAt(STAGE_LABELS[meeting.failed_stage])}
            </p>
          ) : null}
          <p className="text-ink-muted">{meeting.error_message}</p>
        </div>
      </Notice>
      <RetryButton meeting={meeting} />
    </div>
  )
}

// Transcrita sem nomes: o próximo passo é a tela de nomeação (`participants` 25).
function NamingCall({ meeting }: { meeting: MeetingDetail }) {
  if (meeting.status !== "transcribed" || meeting.participants_confirmed)
    return null
  return (
    <section className="flex flex-col items-start gap-3 border-t border-ink pt-4">
      <p className="text-sm text-ink-muted">{MESSAGES.nameParticipantsHint}</p>
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
    <section className="flex flex-col items-start gap-3 border-t border-ink pt-4">
      <p className="text-sm text-ink-muted">{MESSAGES.splitMeetingHint}</p>
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
    <div className="flex flex-col gap-8">
      <Link
        to="/"
        className="inline-flex items-center gap-2 self-start rounded-sm text-sm text-ink-muted outline-none hover:text-ink focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      {error ? (
        <Notice variant="error">
          {error.status === 404 ? MESSAGES.notFound : error.message}
        </Notice>
      ) : isPending ? (
        <SkeletonGroup label={MESSAGES.loading}>
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="h-32" />
        </SkeletonGroup>
      ) : (
        <>
          <TitleEditor
            key={meeting.title}
            id={meeting.id}
            title={meeting.title}
            description={<StatusBadge status={meeting.status} />}
          />
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
              className="self-start rounded-sm text-sm font-medium text-ink underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {MESSAGES.openTranscript}
            </Link>
          ) : null}
          <div className="border-t border-hairline pt-6">
            <DeleteMeetingDialog meetingId={meeting.id} />
          </div>
        </>
      )}
    </div>
  )
}
