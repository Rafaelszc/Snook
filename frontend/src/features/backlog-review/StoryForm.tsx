import { useId, useState } from "react"

import { FormField } from "@/components/forms/FormField"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

import { PRIORITIES, STORY_POINTS } from "./api"
import { useReview } from "./context"
import { TEXTAREA } from "./EditableField"
import { MESSAGES } from "./messages"
import { useBacklogMutation } from "./useBacklog"

const EMPTY = {
  name: "",
  as_a: "",
  i_want: "",
  so_that: "",
  priority: "Medium",
  story_points: "3",
  requested_by: "",
  requested_at: "",
  given: "",
  when: "",
  then: "",
}
type Draft = typeof EMPTY

const SELECT =
  "h-10 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"

function body(draft: Draft) {
  return {
    name: draft.name,
    as_a: draft.as_a,
    i_want: draft.i_want,
    so_that: draft.so_that,
    priority: draft.priority,
    story_points: Number(draft.story_points),
    requested_by: draft.requested_by ? Number(draft.requested_by) : null,
    requested_at: draft.requested_at.trim() || null,
    acceptance_criteria: [
      { given: draft.given, when: draft.when, then: draft.then },
    ],
  }
}

// Nova US na Epic, com um critério; solicitante e instante opcionais (`backlog-review` 17, 18).
export function StoryForm({
  epicId,
  onDone,
}: {
  epicId: number
  onDone: () => void
}) {
  const id = useId()
  const { meetingId, participants } = useReview()
  const [draft, setDraft] = useState(EMPTY)
  const create = useBacklogMutation(meetingId, (input: Draft) =>
    api.post(`/meetings/${meetingId}/epics/${epicId}/user-stories`, body(input))
  )
  const fields = create.error?.fields ?? {}
  const set = (key: keyof Draft) => (event: { target: { value: string } }) =>
    setDraft({ ...draft, [key]: event.target.value })
  const errorFor = (key: string) =>
    fields[key] ?? fields[`acceptance_criteria.0.${key}`]
  const known = Object.keys(fields).length > 0

  const text = (key: "as_a" | "i_want" | "so_that", label: string) => (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={`${id}-${key}`} className="text-sm font-medium">
        {label}
      </label>
      <textarea
        id={`${id}-${key}`}
        value={draft[key]}
        maxLength={2000}
        onChange={set(key)}
        aria-invalid={fields[key] ? true : undefined}
        aria-describedby={fields[key] ? `${id}-${key}-error` : undefined}
        className={TEXTAREA}
      />
      {fields[key] ? (
        <p id={`${id}-${key}-error`} className="text-sm text-destructive">
          {fields[key]}
        </p>
      ) : null}
    </div>
  )

  return (
    <form
      aria-label={MESSAGES.newStory}
      className="motion-enter rounded-xl flex flex-col gap-4 border border-border p-4 sm:p-5"
      onSubmit={(event) => {
        event.preventDefault()
        create.mutate(draft, { onSuccess: onDone })
      }}
    >
      <FormField
        label={MESSAGES.storyName}
        value={draft.name}
        maxLength={200}
        autoFocus
        onChange={set("name")}
        error={fields.name}
      />
      {text("as_a", MESSAGES.asA)}
      {text("i_want", MESSAGES.iWant)}
      {text("so_that", MESSAGES.soThat)}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${id}-priority`} className="text-sm font-medium">
            {MESSAGES.priority}
          </label>
          <select
            id={`${id}-priority`}
            value={draft.priority}
            onChange={set("priority")}
            className={SELECT}
          >
            {PRIORITIES.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${id}-points`} className="text-sm font-medium">
            {MESSAGES.storyPoints}
          </label>
          <select
            id={`${id}-points`}
            value={draft.story_points}
            onChange={set("story_points")}
            className={SELECT}
          >
            {STORY_POINTS.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${id}-requester`} className="text-sm font-medium">
            {MESSAGES.requester}
          </label>
          <select
            id={`${id}-requester`}
            value={draft.requested_by}
            onChange={set("requested_by")}
            className={SELECT}
          >
            <option value="">{MESSAGES.noRequester}</option>
            {participants.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {fields.requested_by ? (
            <p className="text-sm text-destructive">{fields.requested_by}</p>
          ) : null}
        </div>
        <FormField
          label={MESSAGES.requestedAt}
          value={draft.requested_at}
          maxLength={8}
          className="font-mono tabular-nums"
          onChange={set("requested_at")}
          hint={MESSAGES.requestedAtHint}
          error={fields.requested_at}
        />
      </div>
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-sm font-medium">
          {MESSAGES.criteria}
        </legend>
        <FormField
          label={MESSAGES.given}
          value={draft.given}
          maxLength={1000}
          onChange={set("given")}
          error={errorFor("given")}
        />
        <FormField
          label={MESSAGES.when}
          value={draft.when}
          maxLength={1000}
          onChange={set("when")}
          error={errorFor("when")}
        />
        <FormField
          label={MESSAGES.then}
          value={draft.then}
          maxLength={1000}
          onChange={set("then")}
          error={errorFor("then")}
        />
      </fieldset>
      {create.error && !known ? (
        <p role="alert" className="text-sm text-destructive">
          {create.error.message}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? MESSAGES.saving : MESSAGES.createStory}
        </Button>
        <Button type="button" variant="secondary" onClick={onDone}>
          {MESSAGES.cancel}
        </Button>
      </div>
    </form>
  )
}
