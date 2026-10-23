import { useMutation, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api/client"
import type { ApiError } from "@/lib/api/errors"

import { meQueryKey, type RegisterInput, type User } from "./api"

// O cadastro já abre a sessão (cookie HttpOnly); o Usuário vai direto ao cache.
export function useRegister() {
  const queryClient = useQueryClient()
  return useMutation<User, ApiError, RegisterInput>({
    mutationFn: (input) => api.post<User>("/auth/register", input),
    onSuccess: (user) => queryClient.setQueryData(meQueryKey, user),
  })
}
