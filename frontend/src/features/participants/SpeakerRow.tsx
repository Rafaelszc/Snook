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
  readOnly: boolean
  onTogglePlay: () => void
  onNameChange: (name: string) => void
}

export function SpeakerRow({
  speaker,
  name,
  playing,
  mergedWith,
  error,
  readOnly,
  onTogglePlay,
  onNameChange,
}: SpeakerRowProps) {
  const label = speaker.speaker_label
  const inputId = `name-${label}`
  const noteId = `${inputId}-note`
  const note = error ?? (mergedWith ? MESSAGES.mergedWith(mergedWith) : null)

  return (
    <li className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-4 gap-y-2 border-b border-hairline py-4 first:border-t">
      <Button
        type="button"
        variant={playing ? "primary" : "secondary"}
        size="icon"
        aria-label={playing ? MESSAGES.pause(label) : MESSAGES.play(label)}
        aria-pressed={playing}
        onClick={onTogglePlay}
        className="row-start-2 size-10"
      >
        {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
      </Button>
      <div className="col-start-2 flex items-baseline justify-between gap-3 text-sm">
        <label htmlFor={inputId} className="font-medium text-ink">
          <span className="sr-only">{MESSAGES.namePrefix}</span>
          <span translate="no" className="font-mono">
            {label}
          </span>
        </label>
        <span className="text-ink-muted">
          <span className="sr-only">{MESSAGES.speechTime}: </span>
          <span className="font-mono tabular-nums">
            {formatSpeech(speaker.total_seconds)}
          </span>
        </span>
      </div>
      <div className="col-start-2 row-start-2 flex flex-col gap-1.5">
        <Input
          id={inputId}
          name={`names.${label}`}
          value={name}
          maxLength={100}
          autoComplete="off"
          spellCheck={false}
          readOnly={readOnly}
          aria-invalid={error ? true : undefined}
          aria-describedby={note ? noteId : undefined}
          onChange={(event) => onNameChange(event.target.value)}
        />
        {note ? (
          <p
            id={noteId}
            key={error ? "error" : "merged"}
            className={
              error
                ? "motion-enter text-sm text-failed"
                : "motion-enter text-sm text-signal"
            }
          >
            {note}
          </p>
        ) : null}
      </div>
    </li>
  )
}
