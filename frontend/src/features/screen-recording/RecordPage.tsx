import { useCallback, useId, useState } from "react"
import { Mic, Upload } from "lucide-react"
import { Link, useNavigate } from "react-router"

import { ConsentNotice } from "@/components/surfaces/ConsentNotice/ConsentNotice"
import { Button } from "@/components/ui/button"

import type {
  BrowserEnv,
  Clock,
  DisplayCapture,
  MicCapture,
  Recorder,
} from "./capture/interfaces"
import { browserDisplay, browserMic, systemClock } from "./capture/media"
import { mixSources, type Mix } from "./capture/mixer"
import { createRecorder } from "./capture/recorder"
import { MESSAGES } from "./messages"
import { RecordingPanel } from "./RecordingPanel"
import { SendRecordingPage } from "./SendRecordingPage"
import { SourceWarningDialog } from "./SourceWarningDialog"
import { browserEnv, checkSupport } from "./support"
import { useLeaveGuard } from "./useLeaveGuard"
import { useRecording } from "./useRecording"
import { useRecordingSession, type Sources } from "./useRecordingSession"

// Seams do navegador (ADR-0015); testes passam fakes.
export interface RecordDeps {
  env: BrowserEnv
  display: DisplayCapture
  mic: MicCapture
  recorder: Recorder
  mix: (sources: Sources) => Mix
  clock: Clock
}

function useDeps(deps: Partial<RecordDeps>): RecordDeps {
  const [resolved] = useState<RecordDeps>(() => ({
    env: deps.env ?? browserEnv(),
    display: deps.display ?? browserDisplay,
    mic: deps.mic ?? browserMic,
    recorder: deps.recorder ?? createRecorder(),
    mix: deps.mix ?? mixSources,
    clock: deps.clock ?? systemClock,
  }))
  return resolved
}

// Entrada, gravação e envio na mesma página: o áudio só existe na memória dela.
// Tamanhos de texto: sm, base, 2xl.
export function RecordPage({ deps = {} }: { deps?: Partial<RecordDeps> }) {
  const { env, display, mic, recorder, mix, clock } = useDeps(deps)
  const navigate = useNavigate()
  const [support] = useState(() => checkSupport(env))
  const recording = useRecording({ recorder, mix, clock })
  const session = useRecordingSession({
    display,
    mic,
    onReady: recording.begin,
  })
  const pending =
    recording.state.kind === "recording" ||
    recording.state.kind === "stopping" ||
    recording.state.kind === "stopped"
  const release = useLeaveGuard(pending)
  const supportId = useId()

  const onSent = useCallback(
    (id: string) => {
      release()
      navigate(`/meetings/${id}`)
    },
    [navigate, release]
  )

  if (recording.state.kind === "stopped") {
    return (
      <SendRecordingPage
        recording={recording.state.recording}
        onSent={onSent}
      />
    )
  }

  const busy = pending || session.state.kind === "requesting" || support.blocked
  const refusal =
    session.state.kind === "refused"
      ? session.state.message
      : recording.state.kind === "failed"
        ? recording.state.message
        : null

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 py-4 pb-32">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-balance">
          {MESSAGES.recordTitle}
        </h1>
        <p className="text-sm text-muted-foreground">
          {MESSAGES.recordDescription}
        </p>
      </header>
      <section className="flex flex-col gap-4 rounded-xl border border-border p-5">
        <p className="text-base">{MESSAGES.recordHowTo}</p>
        {support.blocked ? (
          <p id={supportId} className="text-sm text-muted-foreground">
            {support.message}
          </p>
        ) : support.warning ? (
          <p className="text-sm text-muted-foreground">{support.warning}</p>
        ) : null}
        {refusal ? (
          <p
            role="alert"
            className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {refusal}
          </p>
        ) : null}
        {pending ? (
          <p className="text-sm text-muted-foreground">{MESSAGES.keepOpen}</p>
        ) : null}
        <div className="flex flex-col gap-3 border-t border-border pt-4">
          <ConsentNotice />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button
              disabled={busy}
              aria-describedby={support.blocked ? supportId : undefined}
              onClick={() => void session.start()}
            >
              <Mic aria-hidden="true" />
              {MESSAGES.record}
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/meetings/new">
                <Upload aria-hidden="true" />
                {MESSAGES.uploadInstead}
              </Link>
            </Button>
          </div>
        </div>
      </section>
      {session.state.kind === "missing" ? (
        <SourceWarningDialog
          missing={session.state.missing}
          onConfirm={session.confirm}
          onCancel={session.cancel}
        />
      ) : null}
      {recording.state.kind === "recording" ||
      recording.state.kind === "stopping" ? (
        <RecordingPanel
          startedAt={recording.state.startedAt}
          clock={clock}
          stopping={recording.state.kind === "stopping"}
          onStop={() => void recording.stop()}
        />
      ) : null}
    </div>
  )
}
