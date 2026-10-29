import type { Sources } from "../useRecordingSession"

export type AudioGraph = Pick<
  AudioContext,
  "createMediaStreamSource" | "createMediaStreamDestination" | "close"
>

export interface Mix {
  stream: MediaStream
  close(): Promise<void>
}

// Web Audio junta as fontes numa trilha só (ADR-0015, Q42). O destino só tem áudio: vídeo da tela fica de fora.
export function mixSources(
  sources: Sources,
  createContext: () => AudioGraph = () => new AudioContext()
): Mix {
  const context = createContext()
  const destination = context.createMediaStreamDestination()
  for (const stream of [sources.display, sources.mic]) {
    if (stream) context.createMediaStreamSource(stream).connect(destination)
  }
  return { stream: destination.stream, close: () => context.close() }
}
