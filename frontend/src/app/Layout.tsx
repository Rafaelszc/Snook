import { Outlet, useNavigate } from "react-router"

import { AppShell } from "@/components/surfaces/AppShell"
import { useLogout, useSession } from "@/features/auth/useSession"

const links = [
  { to: "/", label: "Reuniões" },
  { to: "/settings", label: "Configurações" },
]

// Guarda sessão, logout e links; o AppShell só desenha (ADR-0024).
export function Layout() {
  const navigate = useNavigate()
  const { data: user } = useSession()
  const logout = useLogout()

  function onLogout() {
    logout.mutate(undefined, {
      onSettled: () => navigate("/login", { replace: true }),
    })
  }

  return (
    <AppShell
      links={links}
      userName={user?.username}
      onLogout={onLogout}
      logoutPending={logout.isPending}
    >
      <Outlet />
    </AppShell>
  )
}
