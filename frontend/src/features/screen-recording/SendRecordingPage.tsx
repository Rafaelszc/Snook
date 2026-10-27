import { useState, type FormEvent } from "react"
import { FileAudio, RotateCcw } from "lucide-react"

import { FormField } from "@/components/forms/FormField"
import { Button } from "@/components/ui/button"

import { recordingFileName } from "./fileName"
import { MESSAGES } from "./messages"
import type { Recording } from "./useRecording"
import { useSendRecording } from "./useSendRecording"

function formatBytes(bytes: number): string {
  const mb = bytes / 1024 / 1024
  return `${mb.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}\u00a0MB`
}

// Envio da gravação parada; o arquivo fica na memória para "Tentar de novo" (`screen-recording` 14 a 20).
// Tamanhos de texto: sm, base, 2xl.
export function SendRecordingPage({
  recording,
  onSent,
}: {
  recording: Recording
  onSent: (meetingId: string) => void
}) {
  const send = useSendRecording()
  const [file] = useState(
    () =>
      new File([recording.blob], recordingFileName(recording.startedAt), {
        type: "audio/webm",
      })
  )
  const [title, setTitle] = useState(file.name)
  const [speakers, setSpeakers] = useState("")

  function submit() {
    send.mutate(
      { file, title, expectedSpeakers: speakers },
      { onSuccess: (meeting) => onSent(meeting.id) }
    )
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    submit()
  }

  const apiError = send.error
  const fields = apiError?.fields ?? {}
  const network = apiError?.code === "network_error"
  const generalError =
    apiError && !fields.title && !fields.expected_speakers
      ? network
        ? MESSAGES.networkError
        : apiError.message
      : null
  const percent = Math.round(send.progress * 100)

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 py-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-balance">
          {MESSAGES.sendTitle}
        </h1>
        <p className="text-sm text-muted-foreground">
          {MESSAGES.sendDescription}
        </p>
      </header>
      {recording.limitReached ? (
        <p className="rounded-lg border border-border bg-muted px-3 py-2 text-sm">
          {MESSAGES.limitReached}
        </p>
      ) : null}
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-5">
        <div className="flex items-center gap-3 rounded-xl border border-border px-4 py-3">
          <FileAudio aria-hidden="true" className="size-5 shrink-0" />
          <div className="flex min-w-0 flex-col">
            <span className="truncate font-mono text-sm" translate="no">
              {file.name}
            </span>
            <span className="font-mono text-sm text-muted-foreground tabular-nums">
              {formatBytes(file.size)}
            </span>
          </div>
        </div>
        <FormField
          label={MESSAGES.title}
          hint={MESSAGES.titleHint}
          error={fields.title}
          value={title}
          maxLength={200}
          disabled={send.isPending}
          onChange={(e) => setTitle(e.target.value)}
        />
        <FormField
          label={MESSAGES.speakers}
          hint={MESSAGES.speakersHint}
          error={fields.expected_speakers}
          type="number"
          inputMode="numeric"
          min={1}
          max={20}
          value={speakers}
          disabled={send.isPending}
          onChange={(e) => setSpeakers(e.target.value)}
          className="sm:max-w-40"
        />
        {generalError ? (
          <p
            role="alert"
            className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {generalError}
          </p>
        ) : null}
        <div className="flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center">
          {network && !send.isPending ? (
            <Button type="button" onClick={submit}>
              <RotateCcw aria-hidden="true" />
              {MESSAGES.retry}
            </Button>
          ) : (
            <Button type="submit" disabled={send.isPending}>
              {send.isPending ? MESSAGES.sending : MESSAGES.send}
            </Button>
          )}
          {send.isPending ? (
            <div className="flex flex-1 items-center gap-3">
              <progress
                aria-label={MESSAGES.progress}
                max={100}
                value={percent}
                className="h-1.5 flex-1 accent-foreground"
              />
              <span
                role="status"
                className="font-mono text-sm text-muted-foreground tabular-nums"
              >
                {percent}%
              </span>
            </div>
          ) : null}
        </div>
      </form>
    </div>
  )
}
