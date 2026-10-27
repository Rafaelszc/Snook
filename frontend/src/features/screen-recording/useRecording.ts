import { useCallback, useEffect, useRef, useState } from "react"

import type { Clock, Recorder } from "./capture/interfaces"
import { mixSources, type Mix } from "./capture/mixer"
import { MAX_RECORDING_SECONDS } from "./capture/recorder"
import { MESSAGES } from "./messages"
import { stopAll, type Sources } from "./useRecordingSession"

export interface Recording {
  blob: Blob
  startedAt: number
  limitReached: boolean
}

export type RecordingState =
  | { kind: "idle" }
  | { kind: "recording"; startedAt: number }
  | { kind: "stopping" }
  | { kind: "stopped"; recording: Recording }
  | { kind: "failed"; message: string }

interface Active {
  startedAt: number
  release(): void
}

// Grava a mistura das fontes até "Parar", fim do compartilhamento ou 1h59m50s (`screen-recording` 8, 10, 11, 13).
export function useRecording({
  recorder,
  mix = mixSources,
  clock,
}: {
  recorder: Recorder
  mix?: (sources: Sources) => Mix
  clock: Clock
}) {
  const [state, setState] = useState<RecordingState>({ kind: "idle" })
  const active = useRef<Active | null>(null)

  const stop = useCallback(
    async (limitReached = false) => {
      const current = active.current
      if (!current) return
      active.current = null
      setState({ kind: "stopping" })
      const blob = await recorder.stop()
      current.release()
      setState({
        kind: "stopped",
        recording: { blob, startedAt: current.startedAt, limitReached },
      })
    },
    [recorder]
  )

  const begin = useCallback(
    (sources: Sources) => {
      if (active.current) return
      const mixed = mix(sources)
      try {
        recorder.start(mixed.stream)
      } catch {
        stopAll(sources.display, sources.mic)
        void mixed.close()
        setState({ kind: "failed", message: MESSAGES.recordFailed })
        return
      }
      const startedAt = clock.now()
      const timer = setTimeout(
        () => void stop(true),
        MAX_RECORDING_SECONDS * 1000
      )
      // Chrome encerra as trilhas da tela quando o usuário para pela barra do navegador.
      const onEnded = () => void stop()
      const displayTracks = sources.display?.getTracks() ?? []
      for (const track of displayTracks) {
        track.addEventListener("ended", onEnded)
      }
      active.current = {
        startedAt,
        release() {
          clearTimeout(timer)
          for (const track of displayTracks) {
            track.removeEventListener("ended", onEnded)
          }
          stopAll(sources.display, sources.mic)
          void mixed.close()
        },
      }
      setState({ kind: "recording", startedAt })
    },
    [clock, mix, recorder, stop]
  )

  // Saída confirmada no meio da gravação: descarta o áudio e solta tela e microfone.
  useEffect(
    () => () => {
      const current = active.current
      if (!current) return
      active.current = null
      recorder.stop().catch(() => {})
      current.release()
    },
    [recorder]
  )

  return { state, begin, stop }
}
