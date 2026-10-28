import { useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"

import {
  canName,
  type LlmConfigState,
  type MeetingNamingState,
  type Speaker,
} from "./api"

export function useNamingMeeting(meetingId: string) {
  return useQuery<MeetingNamingState, ApiError>({
    queryKey: ["meetings", meetingId, "naming"],
    queryFn: ({ signal }) =>
      api.get<MeetingNamingState>(`/meetings/${meetingId}`, signal),
  })
}

export function useSpeakers(meetingId: string, meeting?: MeetingNamingState) {
  return useQuery<Speaker[], ApiError>({
    queryKey: ["meetings", meetingId, "speakers"],
    queryFn: ({ signal }) =>
      api.get<Speaker[]>(`/meetings/${meetingId}/speakers`, signal),
    enabled: meeting !== undefined && canName(meeting),
  })
}

// Só exibe o provedor ativo; a escolha mora em Configurações (Q35).
export function useActiveProvider() {
  const query = useQuery<LlmConfigState[], ApiError>({
    queryKey: ["llm-configs"],
    queryFn: ({ signal }) => api.get<LlmConfigState[]>("/llm-configs", signal),
  })
  return {
    ...query,
    active: query.data?.find((config) => config.state === "active") ?? null,
  }
}
