import { ArrowLeft } from "lucide-react"
import { useRef, useState, type FormEvent } from "react"
import { Link, useNavigate, useParams } from "react-router"

import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"
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

function ProviderNote({ active }: { active: LlmConfigState | null }) {
  if (!active)
    return (
      <Notice variant="warn" role="alert">
        <div className="flex flex-col gap-2">
          <p>{MESSAGES.noProvider}</p>
          <Link
            to="/settings"
            className="self-start rounded-sm font-medium text-ink underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {MESSAGES.openSettings}
          </Link>
        </div>
      </Notice>
    )
  return (
    <p className="text-sm text-ink-muted">
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
        <Notice variant="error">{MESSAGES.sampleError}</Notice>
      ) : null}
      <section className="flex flex-col gap-2 border-t border-ink pt-4">
        <h2 className="text-sm font-medium text-ink">
          {MESSAGES.providerTitle}
        </h2>
        <ProviderNote active={active} />
      </section>
      {confirm.error ? (
        <Notice variant="error">{confirm.error.message}</Notice>
      ) : null}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button
          type="submit"
          variant="accent"
          disabled={!allNamed || !active || confirm.isPending}
          aria-describedby="naming-status"
        >
          {confirm.isPending ? MESSAGES.confirming : MESSAGES.confirm}
        </Button>
        <p
          id="naming-status"
          aria-live="polite"
          className="text-sm text-ink-muted"
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
    <div className="flex w-full max-w-reading flex-col gap-6">
      <Link
        to={`/meetings/${id}`}
        className="inline-flex items-center gap-2 self-start rounded-sm text-sm text-ink-muted outline-none hover:text-ink focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        {MESSAGES.back}
      </Link>
      <PageHeader title={MESSAGES.title} description={MESSAGES.description} />
      {error ? (
        <Notice variant="error">
          {error.status === 404 ? MESSAGES.notFound : error.message}
        </Notice>
      ) : meeting.data && !available ? (
        <p className="text-sm text-ink-muted">{MESSAGES.notAvailable}</p>
      ) : !speakers.data || provider.isPending ? (
        <SkeletonGroup label={MESSAGES.loading}>
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </SkeletonGroup>
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
