import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"
import { POLL_INTERVAL_MS } from "@/lib/poll"

import {
  isActive,
  meetingQueryKey,
  meetingsQueryKey,
  type MeetingDetail,
  type MeetingSummary,
} from "./api"

// Polling só com trabalho em andamento; fora disso, nenhum (`meetings` 40; 05-api, "Polling").
export function useMeetings() {
  return useQuery<MeetingSummary[], ApiError>({
    queryKey: meetingsQueryKey,
    queryFn: ({ signal }) => api.get<MeetingSummary[]>("/meetings", signal),
    refetchInterval: ({ state }) =>
      state.data?.some(isActive) ? POLL_INTERVAL_MS : false,
  })
}

export function useMeeting(id: string) {
  return useQuery<MeetingDetail, ApiError>({
    queryKey: meetingQueryKey(id),
    queryFn: ({ signal }) => api.get<MeetingDetail>(`/meetings/${id}`, signal),
    refetchInterval: ({ state }) =>
      state.data && isActive(state.data) ? POLL_INTERVAL_MS : false,
  })
}

// Resposta do servidor vira o cache do detalhe; a lista recarrega.
function useDetailMutation<TInput>(
  id: string,
  mutationFn: (input: TInput) => Promise<MeetingDetail>
) {
  const queryClient = useQueryClient()
  return useMutation<MeetingDetail, ApiError, TInput>({
    mutationFn,
    onSuccess: (meeting) => {
      queryClient.setQueryData(meetingQueryKey(id), meeting)
      return queryClient.invalidateQueries({
        queryKey: meetingsQueryKey,
        exact: true,
      })
    },
  })
}

export function useRenameMeeting(id: string) {
  return useDetailMutation(id, (title: string) =>
    api.patch<MeetingDetail>(`/meetings/${id}`, { title })
  )
}

export function useRetryMeeting(id: string) {
  return useDetailMutation(id, () =>
    api.post<MeetingDetail>(`/meetings/${id}/retry`)
  )
}

export function useDeleteMeeting(id: string) {
  const queryClient = useQueryClient()
  return useMutation<void, ApiError, void>({
    mutationFn: () => api.delete<void>(`/meetings/${id}`),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: meetingQueryKey(id) })
      return queryClient.invalidateQueries({
        queryKey: meetingsQueryKey,
        exact: true,
      })
    },
  })
}
