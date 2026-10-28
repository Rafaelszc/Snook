import { ArrowLeft, CircleAlert, Info } from "lucide-react"
import { useMemo } from "react"
import { Link, useParams } from "react-router"

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

const ALERT =
  "rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"

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
      <section
        role="alert"
        className="flex flex-col gap-3 rounded-xl border border-destructive/40 p-4"
      >
        <p className="flex items-start gap-2 text-sm font-medium">
          <CircleAlert
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0 text-destructive"
          />
          {MESSAGES.failed}
        </p>
        {meeting.error_message ? (
          <p className="text-sm text-muted-foreground">
            {meeting.error_message}
          </p>
        ) : null}
        <RetryButton meetingId={meeting.id} />
      </section>
    )
  return (
    <p className="flex items-start gap-2 rounded-xl border border-border p-4 text-sm">
      <Info
        aria-hidden="true"
        className="mt-0.5 size-4 shrink-0 text-muted-foreground"
      />
      {MESSAGES.readOnly(meeting.status)}
    </p>
  )
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
      <div className="flex flex-col gap-1 rounded-xl border border-dashed border-border p-6">
        <p className="text-base font-medium">{MESSAGES.empty}</p>
        {backlog.read_only ? null : (
          <p className="text-sm text-muted-foreground">{MESSAGES.emptyHint}</p>
        )}
      </div>
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
    <div aria-busy="true" className="flex flex-col gap-4">
      <span role="status" className="sr-only">
        {MESSAGES.loading}
      </span>
      <div className="h-10 w-2/3 rounded-lg bg-muted" />
      <div className="h-48 rounded-xl bg-muted" />
    </div>
  )
}

// Tamanhos de texto: sm, base, 2xl.
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
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 py-4">
      <Link
        to={`/meetings/${id}`}
        className="inline-flex items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold break-words">
          {meeting.data?.title ?? MESSAGES.title}
        </h1>
        {meeting.data && backlog.data ? (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
            <StatusBadge status={meeting.data.status} />
            <span>
              {MESSAGES.epics(backlog.data.epics.length)} ·{" "}
              {MESSAGES.stories(total)}
            </span>
          </div>
        ) : null}
      </header>
      {error ? (
        error.status === 409 ? (
          <p className="text-sm text-muted-foreground">{MESSAGES.noBacklog}</p>
        ) : (
          <p role="alert" className={ALERT}>
            {error.status === 404 ? MESSAGES.notFound : error.message}
          </p>
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
