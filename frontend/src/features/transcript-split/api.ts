// 05-api.md, `transcript-split`: corpo do `GET` e do `refresh`.
export interface SplitSegment {
  id: number
  start_seconds: number
  end_seconds: number
  participant: string
  text: string
  tokens: number
}

export interface SplitPart {
  index: number
  first_segment_id: number
  last_segment_id: number
  start_seconds: number
  end_seconds: number
  estimated_tokens: number
  fits: boolean
}

export interface SplitState {
  status: string
  split_reason: string | null
  can_cancel: boolean
  read_only: boolean
  message: string | null
  provider: string | null
  model: string | null
  budget: number | null
  total_tokens: number | null
  segments: SplitSegment[]
  // `id` do último segmento de cada Parte, menos a última.
  cuts: number[]
  parts: SplitPart[]
}

export interface SplitStatus {
  status: string
}

// Parte por posições na lista de segmentos, `first` a `last` inclusivas.
export interface ClientPart {
  index: number
  first: number
  last: number
  startSeconds: number
  endSeconds: number
  tokens: number
  fits: boolean
}

// `cuts`: posições ordenadas do último segmento de cada Parte, menos a última.
// Estimativa aditiva (ADR-0011): Parte = soma dos segmentos; cabe só com orçamento positivo.
export function partsFromCuts(
  segments: SplitSegment[],
  cuts: readonly number[],
  budget: number
): ClientPart[] {
  if (segments.length === 0) return []
  const ends = [...cuts, segments.length - 1]
  let first = 0
  return ends.map((last, i) => {
    let tokens = 0
    for (let p = first; p <= last; p++) tokens += segments[p].tokens
    const part: ClientPart = {
      index: i + 1,
      first,
      last,
      startSeconds: segments[first].start_seconds,
      endSeconds: segments[last].end_seconds,
      tokens,
      fits: budget > 0 && tokens <= budget,
    }
    first = last + 1
    return part
  })
}

// `id` de segmento -> posição; ignora `id` desconhecido.
export function cutPositions(
  segments: SplitSegment[],
  cutIds: readonly number[]
): number[] {
  const position = new Map(segments.map((s, i) => [s.id, i]))
  return cutIds
    .map((id) => position.get(id))
    .filter((p): p is number => p !== undefined && p < segments.length - 1)
    .sort((a, b) => a - b)
}
