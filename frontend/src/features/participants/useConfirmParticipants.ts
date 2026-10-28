import { useMutation, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"

import type { Participant } from "./api"

// Grava os nomes; a Reunião segue sozinha para a geração (`participants` 6, 31).
export function useConfirmParticipants(meetingId: string) {
  const queryClient = useQueryClient()
  return useMutation<Participant[], ApiError, Record<string, string>>({
    mutationFn: (names) =>
      api.put<Participant[]>(`/meetings/${meetingId}/participants`, {
        names,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["meetings"] }),
  })
}
