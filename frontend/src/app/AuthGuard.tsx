import { Navigate, Outlet, useLocation } from "react-router"

import { useSession } from "@/features/auth/useSession"

// Página protegida sem sessão vai ao login e volta depois (`auth` 24).
export function AuthGuard() {
  const location = useLocation()
  const session = useSession()

  if (session.isPending) {
    return (
      <p role="status" className="sr-only">
        Carregando sessão…
      </p>
    )
  }
  if (session.isError) {
    return (
      <main className="grid min-h-svh place-items-center p-4">
        <p role="alert" className="text-sm text-destructive">
          {session.error.message}
        </p>
      </main>
    )
  }
  if (!session.data) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    )
  }
  return <Outlet />
}
