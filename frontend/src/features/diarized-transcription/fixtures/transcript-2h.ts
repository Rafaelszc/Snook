import type { Transcript } from "../api"

export const SEGMENT_SECONDS = 6
export const TRANSCRIPT_2H_COUNT = (2 * 3600) / SEGMENT_SECONDS

// Duas vozes alternando, 1200 segmentos de 6 s: 2 h.
export function transcript2h(): Transcript {
  return {
    segments: Array.from({ length: TRANSCRIPT_2H_COUNT }, (_, i) => ({
      id: i + 1,
      speaker_label: `SPEAKER_0${i % 2}`,
      start_seconds: i * SEGMENT_SECONDS,
      end_seconds: (i + 1) * SEGMENT_SECONDS - 0.5,
      text: `Trecho número ${i + 1} da reunião.`,
    })),
  }
}
