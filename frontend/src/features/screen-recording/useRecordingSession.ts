import { useCallback, useRef, useState } from "react"

import type { DisplayCapture, MicCapture } from "./capture/interfaces"
import { MESSAGES } from "./messages"

export type Source = "display" | "mic"

export interface Sources {
  display?: MediaStream
  mic?: MediaStream
}

export type SessionState =
  | { kind: "idle" }
  | { kind: "requesting" }
  | { kind: "missing"; missing: Source }
  | { kind: "refused"; message: string }
  | { kind: "ready"; sources: Sources }

export function stopAll(...streams: (MediaStream | null | undefined)[]) {
  for (const stream of streams) {
    for (const track of stream?.getTracks() ?? []) track.stop()
  }
}

// Recusa ou falta da permissão vira fonte ausente; o aviso decide o resto.
async function ask(capture: { request(): Promise<MediaStream> }) {
  try {
    return await capture.request()
  } catch {
    return null
  }
}

// Tela primeiro (precisa do gesto do usuário), depois microfone (ADR-0015).
// `onReady` recebe as fontes escolhidas, no mesmo gesto que as liberou.
export function useRecordingSession({
  display,
  mic,
  onReady,
}: {
  display: DisplayCapture
  mic: MicCapture
  onReady?: (sources: Sources) => void
}) {
  const [state, setState] = useState<SessionState>({ kind: "idle" })
  const pending = useRef<Sources>({})

  const start = useCallback(async () => {
    setState({ kind: "requesting" })
    const screenStream = await ask(display)
    const micStream = await ask(mic)
    const hasScreenAudio = (screenStream?.getAudioTracks().length ?? 0) > 0
    const hasMic = (micStream?.getAudioTracks().length ?? 0) > 0

    if (!hasScreenAudio && !hasMic) {
      stopAll(screenStream, micStream)
      setState({ kind: "refused", message: MESSAGES.noSource })
      return
    }
    // Tela sem áudio não serve: encerra o compartilhamento.
    if (!hasScreenAudio) stopAll(screenStream)
    const sources: Sources = {
      ...(hasScreenAudio && screenStream ? { display: screenStream } : {}),
      ...(hasMic && micStream ? { mic: micStream } : {}),
    }
    if (hasScreenAudio && hasMic) {
      setState({ kind: "ready", sources })
      onReady?.(sources)
      return
    }
    pending.current = sources
    setState({ kind: "missing", missing: hasScreenAudio ? "mic" : "display" })
  }, [display, mic, onReady])

  const confirm = useCallback(() => {
    const sources = pending.current
    pending.current = {}
    setState({ kind: "ready", sources })
    onReady?.(sources)
  }, [onReady])

  const cancel = useCallback(() => {
    stopAll(pending.current.display, pending.current.mic)
    pending.current = {}
    setState({ kind: "idle" })
  }, [])

  return { state, start, confirm, cancel }
}
