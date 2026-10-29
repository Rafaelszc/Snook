import { memo } from "react"

import { api } from "@/lib/api/client"

import { PRIORITIES, STORY_POINTS, type UserStory } from "./api"
import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog"
import { useReview } from "./context"
import { CriteriaList } from "./CriteriaList"
import { EditableField, SelectField } from "./EditableField"
import { MESSAGES } from "./messages"
import { MoveStoryDialog } from "./MoveStoryDialog"
import { useBacklogMutation } from "./useBacklog"

const STORY_NAME_MAX = 200
const STORY_TEXT_MAX = 2000

const PRIORITY_OPTIONS = PRIORITIES.map((p) => ({ value: p, label: p }))
const POINT_OPTIONS = STORY_POINTS.map((p) => ({
  value: String(p),
  label: String(p),
}))

type StoryBody = Partial<{
  name: string
  as_a: string
  i_want: string
  so_that: string
  priority: string
  story_points: number
  requested_by: number | null
  requested_at: string | null
}>

const SENTENCES = [
  { key: "as_a", label: MESSAGES.asA },
  { key: "i_want", label: MESSAGES.iWant },
  { key: "so_that", label: MESSAGES.soThat },
] as const

// US no formato da Q11, com solicitante e instante (`backlog-review` 39, 40).
// Linha com régua --hairline, sem card (ADR-0024, "Componentes"); nome em serif, US-id e instante em mono.
export const StoryCard = memo(function StoryCard({
  story,
  epicId,
}: {
  story: UserStory
  epicId: number
}) {
  const { meetingId, readOnly, participants } = useReview()
  const url = `/meetings/${meetingId}/user-stories/${story.id}`
  const update = useBacklogMutation(meetingId, (body: StoryBody) =>
    api.patch(url, body)
  )
  const remove = useBacklogMutation(meetingId, () => api.delete(url))
  const save = (body: StoryBody) => update.mutateAsync(body)
  const requesterOptions = [
    { value: "", label: MESSAGES.noRequester },
    ...participants.map((p) => ({ value: String(p.id), label: p.name })),
  ]

  return (
    <article
      aria-labelledby={`story-${story.id}`}
      data-slot="story"
      className="flex flex-col gap-4 border-t border-hairline py-4 [contain-intrinsic-size:auto_24rem] [content-visibility:auto]"
    >
      <header className="flex items-start gap-3">
        <span className="shrink-0 pt-1 font-mono text-sm text-ink-muted tabular-nums">
          {story.us_id}
        </span>
        <EditableField
          label={MESSAGES.storyName}
          value={story.name}
          field="name"
          maxLength={STORY_NAME_MAX}
          readOnly={readOnly}
          onSave={(name) => save({ name })}
          className="min-w-0 flex-1"
        >
          <h3
            id={`story-${story.id}`}
            className="pt-1 font-heading text-base font-semibold text-ink"
          >
            {story.name}
          </h3>
        </EditableField>
        {readOnly ? null : (
          <div className="flex shrink-0 items-center gap-1">
            <MoveStoryDialog
              meetingId={meetingId}
              story={story}
              epicId={epicId}
            />
            <ConfirmDeleteDialog
              label={MESSAGES.deleteStory}
              title={MESSAGES.deleteStoryTitle(story.us_id)}
              description={MESSAGES.deleteStoryDescription}
              onConfirm={() => remove.mutateAsync(undefined)}
            />
          </div>
        )}
      </header>
      <dl className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-x-2 gap-y-1 text-sm">
        {SENTENCES.map(({ key, label }) => (
          <div key={key} className="contents">
            <dt className="pt-1 text-ink-muted">{label}</dt>
            <dd>
              <EditableField
                label={label}
                value={story[key]}
                field={key}
                multiline
                maxLength={STORY_TEXT_MAX}
                readOnly={readOnly}
                onSave={(value) => save({ [key]: value })}
                className="pt-1"
              />
            </dd>
          </div>
        ))}
      </dl>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SelectField
          label={MESSAGES.priority}
          value={story.priority}
          field="priority"
          options={PRIORITY_OPTIONS}
          readOnly={readOnly}
          onSave={(priority) => save({ priority })}
        />
        <SelectField
          label={MESSAGES.storyPoints}
          value={String(story.story_points)}
          field="story_points"
          options={POINT_OPTIONS}
          readOnly={readOnly}
          mono
          onSave={(points) => save({ story_points: Number(points) })}
        />
        <SelectField
          label={MESSAGES.requester}
          value={story.requested_by ? String(story.requested_by.id) : ""}
          display={story.requested_by?.name ?? MESSAGES.noRequester}
          field="requested_by"
          options={requesterOptions}
          readOnly={readOnly}
          onSave={(id) => save({ requested_by: id ? Number(id) : null })}
        />
        <div className="flex flex-col gap-1">
          <span className="text-sm text-ink-muted">{MESSAGES.requestedAt}</span>
          <EditableField
            label={MESSAGES.requestedAt}
            value={story.requested_at ?? ""}
            field="requested_at"
            mono
            maxLength={8}
            readOnly={readOnly}
            onSave={(value) => save({ requested_at: value.trim() || null })}
            className="text-sm"
          >
            {story.requested_at ?? "–"}
          </EditableField>
        </div>
      </div>
      <CriteriaList story={story} />
    </article>
  )
})
