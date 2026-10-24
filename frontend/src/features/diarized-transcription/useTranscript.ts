import { useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"
import { POLL_INTERVAL_MS } from "@/lib/poll"

import {
  hasTranscript,
  meetingStatusQueryKey,
  transcriptQueryKey,
  type MeetingStatus,
  type Transcript,
} from "./api"

// Consulta enquanto a Reunião está em `pending` ou `processing` (`diarized-transcription` 27).
export function useMeetingStatus(meetingId: string) {
  return useQuery<MeetingStatus, ApiError>({
    queryKey: meetingStatusQueryKey(meetingId),
    queryFn: ({ signal }) =>
      api.get<MeetingStatus>(`/meetings/${meetingId}`, signal),
    refetchInterval: ({ state }) =>
      state.data && !hasTranscript(state.data) && state.data.status !== "failed"
        ? POLL_INTERVAL_MS
        : false,
  })
}

export function useTranscript(meetingId: string, enabled: boolean) {
  return useQuery<Transcript, ApiError>({
    queryKey: transcriptQueryKey(meetingId),
    queryFn: ({ signal }) =>
      api.get<Transcript>(`/meetings/${meetingId}/transcript`, signal),
    enabled,
  })
}
