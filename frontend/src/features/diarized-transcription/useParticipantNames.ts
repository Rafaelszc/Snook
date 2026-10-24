import { useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"

import { participantsQueryKey, type Participant } from "./api"

const NO_NAMES: ReadonlyMap<string, string> = new Map()

// Rótulo -> nome atual. Lido a cada abertura da tela, para pegar renomeação (`diarized-transcription` 26).
// 404, erro ou lista vazia: mapa vazio, e a tela mostra o rótulo.
export function useParticipantNames(
  meetingId: string,
  enabled: boolean
): ReadonlyMap<string, string> {
  const { data } = useQuery<Participant[], ApiError>({
    queryKey: participantsQueryKey(meetingId),
    queryFn: ({ signal }) =>
      api.get<Participant[]>(`/meetings/${meetingId}/participants`, signal),
    enabled,
    retry: false,
    staleTime: 0,
    refetchOnMount: "always",
  })
  if (!Array.isArray(data) || data.length === 0) return NO_NAMES
  return new Map(
    data.flatMap((p) =>
      p.speaker_labels.map((label) => [label, p.name] as const)
    )
  )
}
