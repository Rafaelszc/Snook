import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"

import {
  llmConfigsQueryKey,
  type ConfigDraft,
  type ConnectionResult,
  type LlmConfig,
  type ModelListResult,
  type Provider,
} from "./api"

export function useLlmConfigs() {
  return useQuery<LlmConfig[], ApiError>({
    queryKey: llmConfigsQueryKey,
    queryFn: ({ signal }) => api.get<LlmConfig[]>("/llm-configs", signal),
  })
}

// Teste não grava nada; só o resultado volta (llm-providers 5).
export function useTestConnection(provider: Provider) {
  return useMutation<ConnectionResult, ApiError, ConfigDraft>({
    mutationFn: (draft) =>
      api.post<ConnectionResult>(`/llm-configs/${provider}/test`, draft),
  })
}

// Lista os modelos que a chave enxerga; não grava nada.
export function useListModels(provider: Provider) {
  return useMutation<ModelListResult, ApiError, ConfigDraft>({
    mutationFn: (draft) =>
      api.post<ModelListResult>(`/llm-configs/${provider}/models`, draft),
  })
}

// Salvar, ativar e remover mudam estados de outros provedores: recarrega a lista.
function useConfigMutation<TResult, TInput>(
  mutationFn: (input: TInput) => Promise<TResult>
) {
  const queryClient = useQueryClient()
  return useMutation<TResult, ApiError, TInput>({
    mutationFn,
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: llmConfigsQueryKey }),
  })
}

export function useSaveConfig(provider: Provider) {
  return useConfigMutation((draft: ConfigDraft) =>
    api.put<LlmConfig>(`/llm-configs/${provider}`, draft)
  )
}

export function useActivateConfig(provider: Provider) {
  return useConfigMutation(() =>
    api.post<LlmConfig>(`/llm-configs/${provider}/activate`)
  )
}

export function useRemoveConfig(provider: Provider) {
  return useConfigMutation(() => api.delete<void>(`/llm-configs/${provider}`))
}
