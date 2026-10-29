import { ArrowLeft } from "lucide-react"
import { useMemo } from "react"
import { Link, useParams } from "react-router"

import { EmptyState } from "@/components/surfaces/EmptyState"
import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"
import { StatusBadge } from "@/components/surfaces/StatusBadge"

import { canRenameParticipant, type Backlog, type ReviewMeeting } from "./api"
import { EpicsContext, ReviewContext, type Review } from "./context"
import { EpicSection } from "./EpicSection"
import { ExportButtons } from "./ExportButtons"
import { MESSAGES } from "./messages"
import { NewEpicForm } from "./NewEpicForm"
import { RegenerateDialog } from "./RegenerateDialog"
import { RenameParticipantDialog } from "./RenameParticipantDialog"
import { RetryButton } from "./RetryButton"
import { useBacklog, useParticipants, useReviewMeeting } from "./useBacklog"

// Só leitura: falha da última geração com motivo e "Tentar novamente", ou situação atual (46).
function ReadOnlyNotice({
  meeting,
  backlog,
}: {
  meeting: ReviewMeeting
  backlog: Backlog
}) {
  if (!backlog.read_only) return null
  if (backlog.last_generation_failed)
    return (
      <Notice variant="warn">
        <div className="flex flex-col gap-3">
          <p className="font-medium">{MESSAGES.failed}</p>
          {meeting.error_message ? (
            <p className="text-ink-muted">{meeting.error_message}</p>
          ) : null}
          <RetryButton meetingId={meeting.id} />
        </div>
      </Notice>
    )
  return <Notice variant="info">{MESSAGES.readOnly(meeting.status)}</Notice>
}

function Actions({
  meeting,
  backlog,
}: {
  meeting: ReviewMeeting
  backlog: Backlog
}) {
  const participants = useParticipants(meeting.id).data ?? []
  return (
    <div className="flex flex-wrap gap-2">
      {backlog.read_only ? null : <RegenerateDialog meetingId={meeting.id} />}
      <ExportButtons meetingId={meeting.id} />
      {canRenameParticipant(meeting) ? (
        <RenameParticipantDialog
          meetingId={meeting.id}
          participants={participants}
        />
      ) : null}
    </div>
  )
}

function Epics({ backlog }: { backlog: Backlog }) {
  if (backlog.epics.length === 0)
    return (
      <EmptyState
        title={MESSAGES.empty}
        description={backlog.read_only ? undefined : MESSAGES.emptyHint}
      />
    )
  return (
    <div className="flex flex-col gap-8">
      {backlog.epics.map((epic) => (
        <EpicSection key={epic.id} epic={epic} />
      ))}
    </div>
  )
}

function Loading() {
  return (
    <SkeletonGroup label={MESSAGES.loading}>
      <Skeleton className="h-10 w-2/3" />
      <Skeleton className="h-48" />
    </SkeletonGroup>
  )
}

// Tamanhos de texto: sm, base, 2xl; lg do EmptyState só sem Epic (aí sem base).
export function ReviewPage() {
  const { id = "" } = useParams()
  const meeting = useReviewMeeting(id)
  const backlog = useBacklog(id, meeting.data?.status)
  const participants = useParticipants(id).data
  const error = meeting.error ?? backlog.error
  const readOnly = backlog.data?.read_only
  const review = useMemo<Review | null>(
    () =>
      readOnly === undefined
        ? null
        : { meetingId: id, readOnly, participants: participants ?? [] },
    [id, readOnly, participants]
  )
  const total =
    backlog.data?.epics.reduce((sum, e) => sum + e.user_stories.length, 0) ?? 0

  return (
    <div className="flex flex-col gap-8">
      <Link
        to={`/meetings/${id}`}
        className="inline-flex items-center gap-2 self-start rounded-sm text-sm text-ink-muted outline-none hover:text-ink focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <PageHeader
        className="break-words"
        title={meeting.data?.title ?? MESSAGES.title}
        description={
          meeting.data && backlog.data ? (
            <span className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <StatusBadge status={meeting.data.status} />
              <span className="font-mono tabular-nums">
                {MESSAGES.epics(backlog.data.epics.length)} ·{" "}
                {MESSAGES.stories(total)}
              </span>
            </span>
          ) : undefined
        }
      />
      {error ? (
        error.status === 409 ? (
          <EmptyState title={MESSAGES.noBacklog} />
        ) : (
          <Notice variant="error">
            {error.status === 404 ? MESSAGES.notFound : error.message}
          </Notice>
        )
      ) : !meeting.data || !backlog.data || !review ? (
        <Loading />
      ) : (
        <ReviewContext.Provider value={review}>
          <EpicsContext.Provider value={backlog.data.epics}>
            <ReadOnlyNotice meeting={meeting.data} backlog={backlog.data} />
            <Actions meeting={meeting.data} backlog={backlog.data} />
            <Epics backlog={backlog.data} />
            {backlog.data.read_only ? null : <NewEpicForm />}
          </EpicsContext.Provider>
        </ReviewContext.Provider>
      )}
    </div>
  )
}
