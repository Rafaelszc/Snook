import { NavLink, Outlet, useNavigate } from "react-router"

import { Button } from "@/components/ui/button"
import { useLogout, useSession } from "@/features/auth/useSession"

const links = [
  { to: "/", label: "Reuniões" },
  { to: "/settings", label: "Configurações" },
]

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
    <div className="min-h-svh">
      <header className="flex items-center justify-between gap-4 p-4">
        <nav aria-label="Principal" className="flex gap-4">
          {links.map(({ to, label }) => (
            <NavLink key={to} to={to} end>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          {user ? (
            <span
              translate="no"
              className="max-w-40 truncate text-sm text-muted-foreground"
            >
              {user.username}
            </span>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            onClick={onLogout}
            disabled={logout.isPending}
          >
            Sair
          </Button>
        </div>
      </header>
      <main className="p-4">
        <Outlet />
      </main>
    </div>
  )
}
