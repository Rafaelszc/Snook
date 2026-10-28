import type { SplitState } from "../api"

export const SEGMENT_SECONDS = 6
export const SPLIT_2H_COUNT = (2 * 3600) / SEGMENT_SECONDS
export const SEGMENT_TOKENS = 100
// 400 segmentos por Parte: 3 Partes na regra gulosa.
export const SPLIT_2H_BUDGET = 400 * SEGMENT_TOKENS

// Duas vozes alternando, 1200 segmentos de 6 s: 2 h.
export function split2h(): SplitState {
  return {
    status: "needs_split",
    split_reason: null,
    can_cancel: false,
    read_only: false,
    message: null,
    provider: "ollama",
    model: "llama3.1:8b",
    budget: SPLIT_2H_BUDGET,
    total_tokens: SPLIT_2H_COUNT * SEGMENT_TOKENS,
    segments: Array.from({ length: SPLIT_2H_COUNT }, (_, i) => ({
      id: i + 1,
      start_seconds: i * SEGMENT_SECONDS,
      end_seconds: (i + 1) * SEGMENT_SECONDS - 0.5,
      participant: i % 2 ? "Bruno" : "Ana",
      text: `Trecho número ${i + 1} da reunião.`,
      tokens: SEGMENT_TOKENS,
    })),
    cuts: [400, 800],
    parts: [],
  }
}
