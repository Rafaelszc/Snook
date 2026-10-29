import type { ReactNode } from "react"
import { Link, NavLink } from "react-router"
import { cn } from "cn"

import { Button } from "@/components/ui/button"

import { SHELL_LABELS } from "./messages"
import { ThemeToggle } from "./ThemeToggle"

export interface ShellLink {
  to: string
  label: string
}

interface AppShellProps {
  links: ShellLink[]
  userName?: string
  onLogout: () => void
  logoutPending?: boolean
  children: ReactNode
}

// Só desenha (ADR-0024, "Componentes"): sessão e logout vêm de app/Layout.tsx.
// Barra opaca, marca em serif, item ativo sublinhado em --signal, conteúdo em --shell.
export function AppShell({
  links,
  userName,
  onLogout,
  logoutPending,
  children,
}: AppShellProps) {
  return (
    <div className="flex min-h-svh flex-col bg-canvas">
      <header className="border-b border-hairline bg-canvas">
        <div className="mx-auto flex w-full max-w-shell flex-wrap items-center gap-x-8 gap-y-2 px-4">
          <Link
            to="/"
            aria-label={SHELL_LABELS.home}
            className="rounded-sm py-3 font-heading text-lg font-semibold text-ink outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {SHELL_LABELS.brand}
          </Link>
          <nav aria-label={SHELL_LABELS.nav} className="flex flex-1 gap-6">
            {links.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end
                className={({ isActive }) =>
                  cn(
                    "border-b-2 py-4 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    isActive
                      ? "border-signal text-ink"
                      : "border-transparent text-ink-muted hover:text-ink"
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            {userName ? (
              <span
                translate="no"
                className="max-w-40 truncate text-sm text-ink-muted"
              >
                {userName}
              </span>
            ) : null}
            <ThemeToggle />
            <Button
              variant="secondary"
              size="sm"
              onClick={onLogout}
              disabled={logoutPending}
            >
              {SHELL_LABELS.logout}
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-shell flex-1 px-4 py-8">
        {children}
      </main>
    </div>
  )
}
