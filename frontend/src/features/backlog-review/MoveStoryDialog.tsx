import { ArrowRightLeft } from "lucide-react"
import { useId, useState } from "react"

import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

import type { UserStory } from "./api"
import { useEpics } from "./context"
import { FormDialog } from "./FormDialog"
import { MESSAGES } from "./messages"
import { useBacklogMutation } from "./useBacklog"

// Mover abre a escolha da Epic de destino entre as da Reunião (`backlog-review` 43).
export function MoveStoryDialog({
  meetingId,
  story,
  epicId,
}: {
  meetingId: string
  story: UserStory
  epicId: number
}) {
  const epics = useEpics()
  const name = useId()
  const others = epics.filter((epic) => epic.id !== epicId)
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState<number>()
  const move = useBacklogMutation(meetingId, (epic_id: number) =>
    api.patch(`/meetings/${meetingId}/user-stories/${story.id}`, { epic_id })
  )

  return (
    <FormDialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        setTarget(others[0]?.id)
        move.reset()
      }}
      trigger={
        <Button variant="ghost" disabled={others.length === 0}>
          <ArrowRightLeft aria-hidden="true" />
          {MESSAGES.moveStory}
        </Button>
      }
      title={MESSAGES.moveTitle(story.us_id)}
      confirm={MESSAGES.moveConfirm}
      pending={move.isPending}
      onSubmit={() => {
        if (target !== undefined)
          move.mutate(target, { onSuccess: () => setOpen(false) })
      }}
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium">
          {MESSAGES.moveTarget}
        </legend>
        {others.map((epic) => (
          <label key={epic.id} className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name={name}
              value={epic.id}
              checked={target === epic.id}
              onChange={() => setTarget(epic.id)}
              className="size-4 accent-foreground"
            />
            <span className="break-words">{epic.name}</span>
          </label>
        ))}
      </fieldset>
      {move.error ? (
        <p role="alert" className="text-sm text-destructive">
          {move.error.message}
        </p>
      ) : null}
    </FormDialog>
  )
}
