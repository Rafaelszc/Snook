import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import { isApiError, type ApiError } from "@/lib/api/errors"

import { meQueryKey, type LoginInput, type User } from "./api"

// Sessão vive só no cookie HttpOnly; o frontend só pergunta `/auth/me`.
// `null` = sem sessão (401). Outro erro sobe para a guarda.
export function useSession() {
  return useQuery<User | null, ApiError>({
    queryKey: meQueryKey,
    queryFn: async ({ signal }) => {
      try {
        return await api.get<User>("/auth/me", signal)
      } catch (error) {
        if (isApiError(error) && error.status === 401) return null
        throw error
      }
    },
    retry: false,
    staleTime: Infinity,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation<User, ApiError, LoginInput>({
    mutationFn: (input) => api.post<User>("/auth/login", input),
    onSuccess: (user) => queryClient.setQueryData(meQueryKey, user),
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation<void, ApiError>({
    mutationFn: () => api.post<void>("/auth/logout"),
    // Sessão já pode ter vencido no servidor: o cliente sai de qualquer jeito.
    onSettled: () => {
      queryClient.removeQueries()
      queryClient.setQueryData(meQueryKey, null)
    },
  })
}
