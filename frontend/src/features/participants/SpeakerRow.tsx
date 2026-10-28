import { Pause, Play } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

import type { Speaker } from "./api"
import { formatSpeech } from "./format"
import { MESSAGES } from "./messages"

interface SpeakerRowProps {
  speaker: Speaker
  name: string
  playing: boolean
  mergedWith: string[] | undefined
  error: string | undefined
  disabled: boolean
  onTogglePlay: () => void
  onNameChange: (name: string) => void
}

export function SpeakerRow({
  speaker,
  name,
  playing,
  mergedWith,
  error,
  disabled,
  onTogglePlay,
  onNameChange,
}: SpeakerRowProps) {
  const label = speaker.speaker_label
  const inputId = `name-${label}`
  const noteId = `${inputId}-note`
  const note = error ?? (mergedWith ? MESSAGES.mergedWith(mergedWith) : null)

  return (
    <li className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-4 gap-y-2 border-b border-border py-4 last:border-b-0">
      <Button
        type="button"
        variant="outline"
        size="icon-lg"
        aria-label={playing ? MESSAGES.pause(label) : MESSAGES.play(label)}
        aria-pressed={playing}
        onClick={onTogglePlay}
        className="row-span-2 mt-6"
      >
        {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
      </Button>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <label htmlFor={inputId} className="font-medium">
          <span className="sr-only">{MESSAGES.namePrefix}</span>
          <span className="font-mono">{label}</span>
        </label>
        <span className="text-muted-foreground">
          <span className="sr-only">{MESSAGES.speechTime}: </span>
          <span className="font-mono tabular-nums">
            {formatSpeech(speaker.total_seconds)}
          </span>
        </span>
      </div>
      <div className="col-start-2 flex flex-col gap-1.5">
        <Input
          id={inputId}
          value={name}
          maxLength={100}
          autoComplete="off"
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={note ? noteId : undefined}
          onChange={(event) => onNameChange(event.target.value)}
        />
        {note ? (
          <p
            id={noteId}
            className={
              error
                ? "text-sm text-destructive"
                : "text-sm text-muted-foreground"
            }
          >
            {note}
          </p>
        ) : null}
      </div>
    </li>
  )
}
