import { useId, useRef, useState, type DragEvent, type FormEvent } from "react"
import { FileAudio, Upload } from "lucide-react"
import { useNavigate } from "react-router"
import { cn } from "cn"

import { FormField } from "@/components/forms/FormField"
import { ConsentNotice } from "@/components/surfaces/ConsentNotice/ConsentNotice"
import { Button } from "@/components/ui/button"
import { usePointerSpotlight } from "@/lib/ui/usePointerSpotlight"

import { MESSAGES } from "./messages"
import { useUpload } from "./useUpload"
import {
  ACCEPTED_EXTENSIONS,
  titleFromFile,
  validateFile,
} from "./validateFile"

const ACCEPT = ACCEPTED_EXTENSIONS.map((ext) => `.${ext}`).join(",")

function formatBytes(bytes: number): string {
  const mb = bytes / 1024 / 1024
  return `${mb.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}\u00a0MB`
}

// Área de soltar com mouse-tracking (ADR-0022, "Mapa de superfícies").
function DropZone({
  file,
  error,
  disabled,
  onFile,
}: {
  file: File | null
  error: string | null
  disabled: boolean
  onFile: (file: File) => void
}) {
  const ref = useRef<HTMLLabelElement>(null)
  const inputId = useId()
  const errorId = `${inputId}-error`
  const [dragging, setDragging] = useState(false)
  usePointerSpotlight(ref)

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped && !disabled) onFile(dropped)
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label
        ref={ref}
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "spotlight flex min-h-44 cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden rounded-xl border border-dashed px-4 py-8 text-center transition-colors has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50",
          dragging ? "border-foreground" : "border-border",
          error && "border-destructive"
        )}
      >
        {file ? (
          <FileAudio aria-hidden="true" className="size-6" />
        ) : (
          <Upload aria-hidden="true" className="size-6 text-muted-foreground" />
        )}
        <span className="text-base font-medium">
          {file ? file.name : MESSAGES.dropTitle}
        </span>
        <span className="text-sm text-muted-foreground">
          {file ? (
            <span className="font-mono tabular-nums">
              {formatBytes(file.size)}
            </span>
          ) : (
            MESSAGES.dropHint
          )}
        </span>
        <input
          id={inputId}
          type="file"
          accept={ACCEPT}
          aria-label={MESSAGES.file}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          disabled={disabled}
          className="sr-only"
          onChange={(e) => {
            const chosen = e.target.files?.[0]
            if (chosen) onFile(chosen)
          }}
        />
      </label>
      {error ? (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function UploadPage() {
  const navigate = useNavigate()
  const upload = useUpload()
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [title, setTitle] = useState("")
  const [speakers, setSpeakers] = useState("")

  function onFile(chosen: File) {
    upload.reset()
    const refusal = validateFile(chosen)
    setFileError(refusal)
    setFile(refusal ? null : chosen)
    if (!refusal) setTitle(titleFromFile(chosen.name))
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!file) {
      setFileError(fileError ?? MESSAGES.fileRequired)
      return
    }
    upload.mutate(
      { file, title, expectedSpeakers: speakers },
      { onSuccess: (meeting) => navigate(`/meetings/${meeting.id}`) }
    )
  }

  const apiError = upload.error
  const fields = apiError?.fields ?? {}
  const generalError =
    apiError && !fields.title && !fields.expected_speakers
      ? apiError.message
      : null
  const percent = Math.round(upload.progress * 100)

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 py-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-balance">
          {MESSAGES.uploadTitle}
        </h1>
        <p className="text-sm text-muted-foreground">
          {MESSAGES.uploadDescription}
        </p>
      </header>
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-5">
        <DropZone
          file={file}
          error={fileError}
          disabled={upload.isPending}
          onFile={onFile}
        />
        <FormField
          label={MESSAGES.title}
          hint={MESSAGES.titleHint}
          error={fields.title}
          value={title}
          maxLength={200}
          disabled={upload.isPending}
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
          disabled={upload.isPending}
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
        <div className="flex flex-col gap-3 border-t border-border pt-5">
          <ConsentNotice />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button type="submit" disabled={upload.isPending}>
              {upload.isPending ? MESSAGES.sending : MESSAGES.send}
            </Button>
            {upload.isPending ? (
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
        </div>
      </form>
    </div>
  )
}
