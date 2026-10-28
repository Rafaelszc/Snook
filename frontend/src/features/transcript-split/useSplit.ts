import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"

import type { SplitState, SplitStatus } from "./api"

// Abre pelo `refresh`, que aplica "passou a caber" (`transcript-split` 47, ADR-0019).
// POST muda estado: roda uma vez por abertura, sem refetch automático.
const splitKey = (meetingId: string) => ["meetings", meetingId, "split"]

// Atualiza a Reunião sem refazer o `refresh` da tela aberta.
function invalidateMeetings(queryClient: QueryClient, meetingId: string) {
  queryClient.removeQueries({ queryKey: splitKey(meetingId) })
  return queryClient.invalidateQueries({ queryKey: ["meetings"] })
}

export function useSplit(meetingId: string) {
  return useQuery<SplitState, ApiError>({
    queryKey: splitKey(meetingId),
    queryFn: () => api.post<SplitState>(`/meetings/${meetingId}/split/refresh`),
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}

// `cuts`: `id` do último segmento de cada Parte, menos a última (`transcript-split` 12).
export function useConfirmSplit(meetingId: string) {
  const queryClient = useQueryClient()
  return useMutation<SplitStatus, ApiError, number[]>({
    mutationFn: (cuts) =>
      api.put<SplitStatus>(`/meetings/${meetingId}/split`, { cuts }),
    onSuccess: () => invalidateMeetings(queryClient, meetingId),
  })
}

export function useCancelSplit(meetingId: string) {
  const queryClient = useQueryClient()
  return useMutation<SplitStatus, ApiError>({
    mutationFn: () =>
      api.post<SplitStatus>(`/meetings/${meetingId}/split/cancel`),
    onSuccess: () => invalidateMeetings(queryClient, meetingId),
  })
}
