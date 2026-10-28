import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"
import { POLL_INTERVAL_MS } from "@/lib/poll"

import {
  backlogKey,
  isActive,
  meetingKey,
  participantsKey,
  type Backlog,
  type Participant,
  type ReviewMeeting,
} from "./api"

export function useReviewMeeting(id: string) {
  return useQuery<ReviewMeeting, ApiError>({
    queryKey: meetingKey(id),
    queryFn: ({ signal }) => api.get<ReviewMeeting>(`/meetings/${id}`, signal),
    refetchInterval: ({ state }) =>
      state.data && isActive(state.data) ? POLL_INTERVAL_MS : false,
  })
}

// `status` na chave: troca de situação (geração terminou) relê o backlog.
export function useBacklog(id: string, status: string | undefined) {
  return useQuery<Backlog, ApiError>({
    queryKey: [...backlogKey(id), status],
    queryFn: ({ signal }) =>
      api.get<Backlog>(`/meetings/${id}/backlog`, signal),
    enabled: status !== undefined,
    placeholderData: (previous) => previous,
  })
}

export function useParticipants(id: string) {
  return useQuery<Participant[], ApiError>({
    queryKey: participantsKey(id),
    queryFn: ({ signal }) =>
      api.get<Participant[]>(`/meetings/${id}/participants`, signal),
  })
}

// Servidor decide junções e ordem: depois de cada escrita, relê backlog e participantes.
function refresh(queryClient: QueryClient, id: string) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: backlogKey(id) }),
    queryClient.invalidateQueries({ queryKey: participantsKey(id) }),
  ])
}

export function useBacklogMutation<TInput, TResult = unknown>(
  id: string,
  mutationFn: (input: TInput) => Promise<TResult>
) {
  const queryClient = useQueryClient()
  return useMutation<TResult, ApiError, TInput>({
    mutationFn,
    onSuccess: () => refresh(queryClient, id),
  })
}

// Regenerar e "Tentar novamente" mudam a situação da Reunião: relê tudo.
export function useMeetingMutation<TInput, TResult = unknown>(
  id: string,
  mutationFn: (input: TInput) => Promise<TResult>
) {
  const queryClient = useQueryClient()
  return useMutation<TResult, ApiError, TInput>({
    mutationFn,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: meetingKey(id) }),
  })
}

// Reunião dividida: `GET /split` em `done` responde só leitura; não dividida, 409.
export function useIsSplit(id: string, enabled: boolean) {
  return useQuery<boolean, ApiError>({
    queryKey: ["meetings", id, "split", "read"],
    queryFn: async ({ signal }) => {
      try {
        const split = await api.get<{ read_only: boolean }>(
          `/meetings/${id}/split`,
          signal
        )
        return split.read_only
      } catch (error) {
        if ((error as ApiError).status === 409) return false
        throw error
      }
    },
    enabled,
    staleTime: 0,
    gcTime: 0,
  })
}
