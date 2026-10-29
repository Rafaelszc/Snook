import { Plus } from "lucide-react"
import { useState } from "react"

import { FormField } from "@/components/forms/FormField"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

import type { Criterion, UserStory } from "./api"
import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog"
import { useReview } from "./context"
import { EditableField } from "./EditableField"
import { MESSAGES } from "./messages"
import { useBacklogMutation } from "./useBacklog"

const CRITERION_MAX = 1000
const PARTS = ["given", "when", "then"] as const
const LABELS = {
  given: MESSAGES.given,
  when: MESSAGES.when,
  then: MESSAGES.then,
}

function CriterionItem({
  criterion,
  last,
}: {
  criterion: Criterion
  last: boolean
}) {
  const { meetingId, readOnly } = useReview()
  const url = `/meetings/${meetingId}/criteria/${criterion.id}`
  const update = useBacklogMutation(meetingId, (body: Partial<Criterion>) =>
    api.patch(url, body)
  )
  const remove = useBacklogMutation(meetingId, () => api.delete(url))

  return (
    <li className="flex items-start gap-2 border-t border-border py-2 first:border-t-0">
      <dl className="grid min-w-0 flex-1 grid-cols-[4.5rem_minmax(0,1fr)] gap-x-2 gap-y-1 text-sm">
        {PARTS.map((part) => (
          <div key={part} className="contents">
            <dt className="pt-1 text-muted-foreground">{LABELS[part]}</dt>
            <dd>
              <EditableField
                label={`${LABELS[part]} do critério`}
                value={criterion[part]}
                field={part}
                multiline
                maxLength={CRITERION_MAX}
                readOnly={readOnly}
                onSave={(value) => update.mutateAsync({ [part]: value })}
                className="pt-1"
              />
            </dd>
          </div>
        ))}
      </dl>
      {readOnly ? null : (
        <ConfirmDeleteDialog
          label={MESSAGES.deleteCriterion}
          title={MESSAGES.deleteCriterionTitle}
          description={MESSAGES.deleteCriterionDescription}
          blockedReason={last ? MESSAGES.lastCriterion : undefined}
          onConfirm={() => remove.mutateAsync(undefined)}
        />
      )}
    </li>
  )
}

const EMPTY = { given: "", when: "", then: "" }

function NewCriterion({ story }: { story: UserStory }) {
  const { meetingId } = useReview()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState(EMPTY)
  const add = useBacklogMutation(meetingId, (body: typeof EMPTY) =>
    api.post(`/meetings/${meetingId}/user-stories/${story.id}/criteria`, body)
  )

  if (!open)
    return (
      <Button
        variant="ghost"
        className="self-start"
        onClick={() => setOpen(true)}
      >
        <Plus aria-hidden="true" />
        {MESSAGES.newCriterion}
      </Button>
    )

  return (
    <form
      className="flex flex-col gap-3 rounded-lg border border-border p-3"
      onSubmit={(event) => {
        event.preventDefault()
        add.mutate(draft, {
          onSuccess: () => {
            setDraft(EMPTY)
            setOpen(false)
          },
        })
      }}
    >
      {PARTS.map((part) => (
        <FormField
          key={part}
          label={LABELS[part]}
          value={draft[part]}
          maxLength={CRITERION_MAX}
          autoFocus={part === "given"}
          error={add.error?.fields[part]}
          onChange={(event) =>
            setDraft({ ...draft, [part]: event.target.value })
          }
        />
      ))}
      {add.error && !PARTS.some((p) => add.error?.fields[p]) ? (
        <p role="alert" className="text-sm text-destructive">
          {add.error.message}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={add.isPending}>
          {add.isPending ? MESSAGES.saving : MESSAGES.createCriterion}
        </Button>
        <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
          {MESSAGES.cancel}
        </Button>
      </div>
    </form>
  )
}

export function CriteriaList({ story }: { story: UserStory }) {
  const { readOnly } = useReview()
  const criteria = story.acceptance_criteria
  return (
    <section className="flex flex-col gap-1">
      <h4 className="text-sm font-medium">{MESSAGES.criteria}</h4>
      <ul>
        {criteria.map((criterion) => (
          <CriterionItem
            key={criterion.id}
            criterion={criterion}
            last={criteria.length === 1}
          />
        ))}
      </ul>
      {readOnly ? null : <NewCriterion story={story} />}
    </section>
  )
}
