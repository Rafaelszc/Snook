import type { ReactNode } from "react"

import { SHELL_LABELS } from "@/components/surfaces/messages"
import { ThemeToggle } from "@/components/surfaces/ThemeToggle"

interface AuthShellProps {
  title: string
  description: string
  children: ReactNode
}

// Card opaco comum a cadastro e login: exceção do card de auth (ADR-0024, Q3).
// --surface, régua --hairline, --r-10, sem sombra, sem vidro e sem mouse-tracking.
// Entrada só por opacidade; motion.css desliga com reduced-motion.
// Tamanhos de texto: sm, base, 2xl.
export function AuthShell({ title, description, children }: AuthShellProps) {
  return (
    <main className="relative grid min-h-svh place-items-center bg-canvas px-4 py-12">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <section
        aria-labelledby="auth-title"
        data-slot="auth-card"
        className="motion-fade-in flex w-full max-w-sm flex-col gap-6 rounded-lg border border-hairline bg-surface p-6 text-ink sm:p-8"
      >
        <header className="flex flex-col gap-2">
          <p
            translate="no"
            className="font-heading text-base font-semibold text-ink"
          >
            {SHELL_LABELS.brand}
          </p>
          <h1
            id="auth-title"
            className="font-heading text-2xl font-semibold text-balance"
          >
            {title}
          </h1>
          <p className="text-sm text-ink-muted">{description}</p>
        </header>
        {children}
      </section>
    </main>
  )
}
