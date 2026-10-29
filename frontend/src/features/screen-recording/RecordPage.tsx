import { useCallback, useId, useState } from "react"
import { Mic, Upload } from "lucide-react"
import { Link, useNavigate } from "react-router"

import { ConsentNotice } from "@/components/surfaces/ConsentNotice/ConsentNotice"
import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
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
    // Folga no rodapé para o painel flutuante não cobrir os botões.
    <div className="flex flex-col gap-8 pb-32">
      <PageHeader
        title={MESSAGES.recordTitle}
        description={MESSAGES.recordDescription}
      />
      <section className="flex max-w-reading flex-col gap-4 border-t border-ink pt-4">
        <p className="font-serif text-base text-ink">{MESSAGES.recordHowTo}</p>
        {support.blocked ? (
          <Notice id={supportId} variant="warn">
            {support.message}
          </Notice>
        ) : support.warning ? (
          <p id={supportId} className="text-sm text-ink-muted">
            {support.warning}
          </p>
        ) : null}
        {refusal ? <Notice variant="error">{refusal}</Notice> : null}
        {pending ? (
          <p className="text-sm text-ink-muted">{MESSAGES.keepOpen}</p>
        ) : null}
        <div className="flex flex-col gap-3 border-t border-hairline pt-4">
          <ConsentNotice />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button
              disabled={busy}
              aria-describedby={
                support.blocked || support.warning ? supportId : undefined
              }
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
          browser={env.browser()}
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
