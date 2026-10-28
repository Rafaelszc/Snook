import { ChevronRight, Plus } from "lucide-react"
import { memo, useState } from "react"

import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

import { mergeTarget, type Epic } from "./api"
import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog"
import { useEpics, useReview } from "./context"
import { EditableField } from "./EditableField"
import { MESSAGES } from "./messages"
import { StoryCard } from "./StoryCard"
import { StoryForm } from "./StoryForm"
import { useBacklogMutation } from "./useBacklog"

export const EPIC_NAME_MAX = 200

// Epic recolhível; abrir e fechar animam só `transform` e `opacity` (ADR-0022).
export const EpicSection = memo(function EpicSection({ epic }: { epic: Epic }) {
  const { meetingId, readOnly } = useReview()
  const epics = useEpics()
  const [open, setOpen] = useState(true)
  const [adding, setAdding] = useState(false)
  const url = `/meetings/${meetingId}/epics/${epic.id}`
  const rename = useBacklogMutation(meetingId, (name: string) =>
    api.patch(url, { name })
  )
  const remove = useBacklogMutation(meetingId, () => api.delete(url))
  const contentId = `epic-${epic.id}-content`
  const count = epic.user_stories.length

  return (
    <section
      aria-labelledby={`epic-${epic.id}`}
      className="flex flex-col gap-3"
    >
      <header className="flex items-start gap-2 border-b border-border pb-2">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-expanded={open}
          aria-controls={contentId}
          aria-label={MESSAGES.toggleEpic(epic.name, open)}
          onClick={() => setOpen(!open)}
          className="mt-0.5 shrink-0"
        >
          <ChevronRight
            aria-hidden="true"
            className={`motion-rise ${open ? "rotate-90" : ""}`}
          />
        </Button>
        <EditableField
          label={`${MESSAGES.epicName} ${epic.name}`}
          value={epic.name}
          field="name"
          maxLength={EPIC_NAME_MAX}
          readOnly={readOnly}
          notice={(draft) => {
            const target = mergeTarget(epics, epic.id, draft)
            return target && MESSAGES.mergeEpic(target.name)
          }}
          onSave={(name) => rename.mutateAsync(name)}
          className="min-w-0 flex-1"
        >
          <h2
            id={`epic-${epic.id}`}
            className="flex flex-wrap items-baseline gap-x-3 pt-0.5"
          >
            <span className="text-base font-semibold">
              <span className="sr-only">{MESSAGES.epic}: </span>
              {epic.name}
            </span>
            <span className="text-sm text-muted-foreground">
              {MESSAGES.stories(count)}
            </span>
          </h2>
        </EditableField>
        {readOnly ? null : (
          <ConfirmDeleteDialog
            label={`${MESSAGES.deleteEpic} ${epic.name}`}
            title={MESSAGES.deleteEpicTitle(epic.name)}
            description={MESSAGES.deleteEpicDescription}
            blockedReason={count > 0 ? MESSAGES.deleteEpicBlocked : undefined}
            onConfirm={() => remove.mutateAsync(undefined)}
          />
        )}
      </header>
      {open ? (
        <div
          id={contentId}
          className="motion-enter flex flex-col gap-3 sm:pl-10"
        >
          {epic.user_stories.map((story) => (
            <StoryCard key={story.id} story={story} epicId={epic.id} />
          ))}
          {readOnly ? null : adding ? (
            <StoryForm epicId={epic.id} onDone={() => setAdding(false)} />
          ) : (
            <Button
              variant="ghost"
              className="self-start"
              onClick={() => setAdding(true)}
            >
              <Plus aria-hidden="true" />
              {MESSAGES.newStory}
            </Button>
          )}
        </div>
      ) : (
        <div id={contentId} hidden />
      )}
    </section>
  )
})
