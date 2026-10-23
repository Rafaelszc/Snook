// 05-api.md, `auth`.
export interface User {
  id: string
  email: string
  username: string
}

export interface RegisterInput {
  email: string
  username: string
  password: string
}

export interface LoginInput {
  identifier: string
  password: string
}

export const meQueryKey = ["auth", "me"] as const
