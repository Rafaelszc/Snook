import { ArrowLeft, CircleAlert } from "lucide-react"
import { useRef, useState, type FormEvent } from "react"
import { Link, useNavigate, useParams } from "react-router"

import { Button } from "@/components/ui/button"

import {
  canName,
  mergeGroups,
  nameKey,
  sampleUrl,
  type LlmConfigState,
  type Speaker,
} from "./api"
import { MESSAGES, PROVIDER_LABELS } from "./messages"
import { SpeakerRow } from "./SpeakerRow"
import { useConfirmParticipants } from "./useConfirmParticipants"
import { useActiveProvider, useNamingMeeting, useSpeakers } from "./useSpeakers"

const ALERT =
  "rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"

function ProviderNote({ active }: { active: LlmConfigState | null }) {
  if (!active)
    return (
      <div role="alert" className={`flex flex-col gap-2 ${ALERT}`}>
        <p className="flex items-start gap-2">
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {MESSAGES.noProvider}
        </p>
        <Link
          to="/settings"
          className="self-start font-medium underline underline-offset-4"
        >
          {MESSAGES.openSettings}
        </Link>
      </div>
    )
  return (
    <p className="text-sm text-muted-foreground">
      {MESSAGES.providerUsed(
        PROVIDER_LABELS[active.provider] ?? active.provider,
        active.model ?? ""
      )}
    </p>
  )
}

function NamingForm({
  meetingId,
  speakers,
  active,
}: {
  meetingId: string
  speakers: Speaker[]
  active: LlmConfigState | null
}) {
  const navigate = useNavigate()
  const confirm = useConfirmParticipants(meetingId)
  const [names, setNames] = useState<Record<string, string>>(() =>
    Object.fromEntries(speakers.map((s) => [s.speaker_label, ""]))
  )
  const [playing, setPlaying] = useState<string | null>(null)
  const [sampleError, setSampleError] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  const merged = mergeGroups(names)
  const allNamed = speakers.every((s) => nameKey(names[s.speaker_label]))
  const participantCount = new Set(Object.values(names).map(nameKey)).size
  const fields = confirm.error?.fields ?? {}

  function togglePlay(label: string) {
    const audio = audioRef.current
    if (!audio) return
    if (playing === label) {
      audio.pause()
      setPlaying(null)
      return
    }
    setSampleError(false)
    audio.src = sampleUrl(meetingId, label)
    setPlaying(label)
    audio.play().catch(() => {
      setPlaying(null)
      setSampleError(true)
    })
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!allNamed || !active) return
    audioRef.current?.pause()
    confirm.mutate(names, {
      onSuccess: () => navigate(`/meetings/${meetingId}`),
      // Foco no primeiro campo recusado pela API.
      onError: (error) => {
        const label = speakers.find(
          (s) => error.fields[`names.${s.speaker_label}`]
        )?.speaker_label
        if (label) document.getElementById(`name-${label}`)?.focus()
      },
    })
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-6">
      <audio
        ref={audioRef}
        preload="none"
        onEnded={() => setPlaying(null)}
        onError={() => {
          setPlaying(null)
          setSampleError(true)
        }}
        className="hidden"
      />
      <ul aria-label={MESSAGES.speakersLabel} className="flex flex-col">
        {speakers.map((speaker) => (
          <SpeakerRow
            key={speaker.speaker_label}
            speaker={speaker}
            name={names[speaker.speaker_label]}
            playing={playing === speaker.speaker_label}
            mergedWith={merged.get(speaker.speaker_label)}
            error={fields[`names.${speaker.speaker_label}`]}
            readOnly={confirm.isPending}
            onTogglePlay={() => togglePlay(speaker.speaker_label)}
            onNameChange={(name) =>
              setNames((prev) => ({ ...prev, [speaker.speaker_label]: name }))
            }
          />
        ))}
      </ul>
      {sampleError ? (
        <p role="alert" className={ALERT}>
          {MESSAGES.sampleError}
        </p>
      ) : null}
      <section className="flex flex-col gap-2 border-t border-border pt-5">
        <h2 className="text-sm font-medium">{MESSAGES.providerTitle}</h2>
        <ProviderNote active={active} />
      </section>
      {confirm.error ? (
        <p role="alert" className={ALERT}>
          {confirm.error.message}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button
          type="submit"
          disabled={!allNamed || !active || confirm.isPending}
          aria-describedby="naming-status"
        >
          {confirm.isPending ? MESSAGES.confirming : MESSAGES.confirm}
        </Button>
        <p
          id="naming-status"
          aria-live="polite"
          className="text-sm text-muted-foreground"
        >
          {allNamed
            ? MESSAGES.summary(speakers.length, participantCount)
            : MESSAGES.missingNames}
        </p>
      </div>
    </form>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function NamingPage() {
  const { id = "" } = useParams()
  const meeting = useNamingMeeting(id)
  const speakers = useSpeakers(id, meeting.data)
  const provider = useActiveProvider()
  const error = meeting.error ?? speakers.error ?? provider.error
  const available = meeting.data !== undefined && canName(meeting.data)

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 py-4">
      <Link
        to={`/meetings/${id}`}
        className="inline-flex items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{MESSAGES.title}</h1>
        <p className="text-base text-muted-foreground">
          {MESSAGES.description}
        </p>
      </header>
      {error ? (
        <p role="alert" className={ALERT}>
          {error.status === 404 ? MESSAGES.notFound : error.message}
        </p>
      ) : meeting.data && !available ? (
        <p className="text-sm text-muted-foreground">{MESSAGES.notAvailable}</p>
      ) : !speakers.data || provider.isPending ? (
        <div aria-busy="true" className="flex flex-col gap-3">
          <span role="status" className="sr-only">
            {MESSAGES.loading}
          </span>
          <div className="h-16 rounded-xl bg-muted" />
          <div className="h-16 rounded-xl bg-muted" />
        </div>
      ) : (
        <NamingForm
          meetingId={id}
          speakers={speakers.data}
          active={provider.active}
        />
      )}
    </div>
  )
}
