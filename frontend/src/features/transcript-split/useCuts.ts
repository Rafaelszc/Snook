import { useMemo, useState } from "react"

import { cutPositions, partsFromCuts, type SplitSegment } from "./api"

// Cortes em posições ordenadas; Partes recalculadas no cliente a cada mudança (`transcript-split` 34).
export function useCuts(
  segments: SplitSegment[],
  initialCutIds: readonly number[],
  budget: number
) {
  const [cuts, setCuts] = useState(() => cutPositions(segments, initialCutIds))
  const parts = useMemo(
    () => partsFromCuts(segments, cuts, budget),
    [segments, cuts, budget]
  )
  const lastBoundary = segments.length - 2

  // Adiciona ou remove o corte no fim do segmento `position` (`transcript-split` 33).
  function toggle(position: number) {
    if (position < 0 || position > lastBoundary) return
    setCuts((prev) =>
      prev.includes(position)
        ? prev.filter((p) => p !== position)
        : [...prev, position].sort((a, b) => a - b)
    )
  }

  // Move para o fim de outro segmento; recusa destino ocupado ou fora da lista.
  function move(from: number, to: number): boolean {
    if (to < 0 || to > lastBoundary || cuts.includes(to)) return false
    if (!cuts.includes(from)) return false
    setCuts((prev) =>
      prev.map((p) => (p === from ? to : p)).sort((a, b) => a - b)
    )
    return true
  }

  return {
    cuts,
    parts,
    cutIds: cuts.map((p) => segments[p].id),
    allFit: parts.every((part) => part.fits),
    toggle,
    move,
  }
}
