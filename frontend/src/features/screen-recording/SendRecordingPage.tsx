import { useState, type FormEvent } from "react"
import { FileAudio, RotateCcw } from "lucide-react"

import { FormField } from "@/components/forms/FormField"
import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
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
    <div className="flex w-full max-w-reading flex-col gap-8">
      <PageHeader
        title={MESSAGES.sendTitle}
        description={MESSAGES.sendDescription}
      />
      {recording.limitReached ? (
        <Notice variant="info">{MESSAGES.limitReached}</Notice>
      ) : null}
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
        <div className="flex items-center gap-3 border-y border-hairline py-3">
          <FileAudio
            aria-hidden="true"
            className="size-5 shrink-0 text-signal"
          />
          <div className="flex min-w-0 flex-col">
            <span className="truncate font-mono text-sm" translate="no">
              {file.name}
            </span>
            <span className="font-mono text-sm text-ink-muted tabular-nums">
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
        {generalError ? <Notice variant="error">{generalError}</Notice> : null}
        <div className="flex flex-col gap-3 border-t border-ink pt-4 sm:flex-row sm:items-center">
          {network && !send.isPending ? (
            <Button type="button" variant="secondary" onClick={submit}>
              <RotateCcw aria-hidden="true" />
              {MESSAGES.retry}
            </Button>
          ) : (
            <Button type="submit" variant="accent" disabled={send.isPending}>
              {send.isPending ? MESSAGES.sending : MESSAGES.send}
            </Button>
          )}
          {send.isPending ? (
            <div className="flex flex-1 items-center gap-3">
              <progress
                aria-label={MESSAGES.progress}
                max={100}
                value={percent}
                className="h-1 flex-1 accent-signal"
              />
              <span
                role="status"
                className="font-mono text-sm text-ink-muted tabular-nums"
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
