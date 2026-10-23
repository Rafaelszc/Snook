import { useState, type FormEvent } from "react"
import { Pencil } from "lucide-react"

import { FormField } from "@/components/forms/FormField"
import { Button } from "@/components/ui/button"

import { MESSAGES } from "./messages"
import { useRenameMeeting } from "./useMeetings"

// Edição de título em qualquer status (`meetings` 41). O título é o h1 da tela.
export function TitleEditor({ id, title }: { id: string; title: string }) {
  const rename = useRenameMeeting(id)
  const [draft, setDraft] = useState<string | null>(null)

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (draft === null) return
    rename.mutate(draft, { onSuccess: () => setDraft(null) })
  }

  if (draft === null)
    return (
      <div className="flex items-start gap-2">
        <h1 className="min-w-0 text-2xl font-semibold text-balance break-words">
          {title}
        </h1>
        <Button
          variant="ghost"
          size="icon"
          aria-label={MESSAGES.editTitle}
          onClick={() => {
            rename.reset()
            setDraft(title)
          }}
        >
          <Pencil aria-hidden="true" />
        </Button>
      </div>
    )

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <h1 className="sr-only">{title}</h1>
      <FormField
        label={MESSAGES.title}
        value={draft}
        maxLength={200}
        autoFocus
        error={rename.error?.fields.title ?? rename.error?.message}
        disabled={rename.isPending}
        onChange={(e) => setDraft(e.target.value)}
      />
      <div className="flex gap-2">
        <Button type="submit" disabled={rename.isPending}>
          {rename.isPending ? MESSAGES.savingTitle : MESSAGES.saveTitle}
        </Button>
        <Button variant="outline" type="button" onClick={() => setDraft(null)}>
          {MESSAGES.cancel}
        </Button>
      </div>
    </form>
  )
}
