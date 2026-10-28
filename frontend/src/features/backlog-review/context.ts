import { createContext, useContext } from "react"

import type { Epic, Participant } from "./api"

// Sem `epics`: os cards memoizados só re-renderizam quando a própria US muda.
export interface Review {
  meetingId: string
  readOnly: boolean
  participants: readonly Participant[]
}

export const ReviewContext = createContext<Review | null>(null)

// Lista de Epics à parte: só quem escolhe destino ou avisa junção depende dela.
export const EpicsContext = createContext<readonly Epic[]>([])

export const useEpics = () => useContext(EpicsContext)

export function useReview(): Review {
  const review = useContext(ReviewContext)
  if (!review) throw new Error("ReviewContext ausente")
  return review
}
