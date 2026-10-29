import { UserPen } from "lucide-react"
import { useId, useState } from "react"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

import { mergeTarget, type Participant } from "./api"
import { fieldError } from "./fieldError"
import { FormDialog } from "./FormDialog"
import { MergeNotice } from "./MergeNotice"
import { MESSAGES } from "./messages"
import { useBacklogMutation } from "./useBacklog"

// "Renomear participante" (`backlog-review` 23 a 25, 41, 48): nome igual une os dois.
export function RenameParticipantDialog({
  meetingId,
  participants,
}: {
  meetingId: string
  participants: readonly Participant[]
}) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [participantId, setParticipantId] = useState<number>()
  const [name, setName] = useState("")
  const rename = useBacklogMutation(
    meetingId,
    (body: { id: number; name: string }) =>
      api.patch(`/meetings/${meetingId}/participants/${body.id}`, {
        name: body.name,
      })
  )
  const target =
    participantId === undefined
      ? undefined
      : mergeTarget(participants, participantId, name)
  const error = rename.error ? fieldError(rename.error, "name") : undefined
  const describedBy =
    [target && `${id}-merge`, error && `${id}-error`]
      .filter(Boolean)
      .join(" ") || undefined

  return (
    <FormDialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        const first = participants[0]
        setParticipantId(first?.id)
        setName(first?.name ?? "")
        rename.reset()
      }}
      trigger={
        <Button variant="secondary" disabled={participants.length === 0}>
          <UserPen aria-hidden="true" />
          {MESSAGES.renameParticipant}
        </Button>
      }
      title={MESSAGES.renameParticipant}
      confirm={MESSAGES.renameConfirm}
      pending={rename.isPending}
      onSubmit={() => {
        if (participantId !== undefined)
          rename.mutate(
            { id: participantId, name },
            { onSuccess: () => setOpen(false) }
          )
      }}
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${id}-who`} className="text-sm font-medium">
          {MESSAGES.participant}
        </label>
        <select
          id={`${id}-who`}
          value={participantId ?? ""}
          onChange={(event) => {
            const chosen = participants.find(
              (p) => p.id === Number(event.target.value)
            )
            setParticipantId(chosen?.id)
            setName(chosen?.name ?? "")
          }}
          className="h-10 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
        >
          {participants.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${id}-name`} className="text-sm font-medium">
          {MESSAGES.newName}
        </label>
        <Input
          id={`${id}-name`}
          value={name}
          maxLength={100}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(event) => setName(event.target.value)}
        />
        <MergeNotice
          id={`${id}-merge`}
          message={target && MESSAGES.mergeParticipant(target.name)}
        />
        {error ? (
          <p
            id={`${id}-error`}
            role="alert"
            className="text-sm text-destructive"
          >
            {error}
          </p>
        ) : null}
      </div>
    </FormDialog>
  )
}
