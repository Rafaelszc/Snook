import { RECORDING_MIME } from "../support"
import type { Recorder } from "./interfaces"

export const AUDIO_BITS_PER_SECOND = 64_000
// 1h59m50s (Q61), abaixo do limite de 2 h.
export const MAX_RECORDING_SECONDS = 7190
// Folga para o contêiner webm.
const CONTAINER_OVERHEAD = 1.05

export function projectedBytes(seconds: number): number {
  return Math.ceil(((seconds * AUDIO_BITS_PER_SECOND) / 8) * CONTAINER_OVERHEAD)
}

export interface MediaRecorderLike {
  start(timeslice?: number): void
  stop(): void
  ondataavailable: ((event: BlobEvent) => void) | null
  onstop: ((event: Event) => void) | null
}

export type MediaRecorderCtor = new (
  stream: MediaStream,
  options: MediaRecorderOptions
) => MediaRecorderLike

// Trechos de 1 s; o Blob final junta todos. `MediaRecorder` só é lido ao gravar:
// navegador sem a API ainda abre a página com o botão desabilitado (`screen-recording` 22).
export function createRecorder(Ctor?: MediaRecorderCtor): Recorder {
  let media: MediaRecorderLike | null = null
  const chunks: Blob[] = []

  return {
    start(stream) {
      chunks.length = 0
      const Impl = Ctor ?? MediaRecorder
      media = new Impl(stream, {
        mimeType: RECORDING_MIME,
        audioBitsPerSecond: AUDIO_BITS_PER_SECOND,
      })
      media.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data)
      }
      media.start(1000)
    },
    stop() {
      const current = media
      if (!current) return Promise.reject(new Error("Recorder not started"))
      return new Promise((resolve) => {
        current.onstop = () => {
          resolve(new Blob(chunks, { type: "audio/webm" }))
        }
        current.stop()
        media = null
      })
    },
  }
}
