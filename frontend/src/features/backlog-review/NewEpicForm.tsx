import { Plus } from "lucide-react"
import { useId, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api/client"

import { mergeTarget } from "./api"
import { useEpics, useReview } from "./context"
import { EPIC_NAME_MAX } from "./EpicSection"
import { fieldError } from "./fieldError"
import { MergeNotice } from "./MergeNotice"
import { MESSAGES } from "./messages"
import { useBacklogMutation } from "./useBacklog"

// Nome existente junta com a Epic existente (Q57); o aviso aparece antes de salvar (41).
export function NewEpicForm() {
  const id = useId()
  const { meetingId } = useReview()
  const epics = useEpics()
  const [name, setName] = useState("")
  const create = useBacklogMutation(meetingId, (value: string) =>
    api.post(`/meetings/${meetingId}/epics`, { name: value })
  )
  const target = mergeTarget(epics, null, name)
  const error = create.error ? fieldError(create.error, "name") : undefined
  const describedBy =
    [target && `${id}-merge`, error && `${id}-error`]
      .filter(Boolean)
      .join(" ") || undefined

  return (
    <form
      className="flex flex-col gap-2 border-t border-border pt-5"
      onSubmit={(event) => {
        event.preventDefault()
        create.mutate(name, { onSuccess: () => setName("") })
      }}
    >
      <label htmlFor={id} className="text-sm font-medium">
        {MESSAGES.newEpic}
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          id={id}
          value={name}
          maxLength={EPIC_NAME_MAX}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(event) => setName(event.target.value)}
        />
        <Button type="submit" disabled={create.isPending} className="shrink-0">
          <Plus aria-hidden="true" />
          {MESSAGES.createEpic}
        </Button>
      </div>
      <MergeNotice
        id={`${id}-merge`}
        message={target && MESSAGES.mergeEpic(target.name)}
      />
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </form>
  )
}
