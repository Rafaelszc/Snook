import { useRef, type ReactNode } from "react"

import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { usePointerSpotlight } from "@/lib/ui/usePointerSpotlight"

interface AuthShellProps {
  title: string
  description: string
  children: ReactNode
}

// Card de vidro com mouse-tracking, comum a cadastro e login (ADR-0022).
// Tamanhos de texto: sm, base, xl.
export function AuthShell({ title, description, children }: AuthShellProps) {
  const ref = useRef<HTMLElement>(null)
  usePointerSpotlight(ref)

  return (
    <main
      ref={ref}
      className="spotlight grid min-h-svh place-items-center px-4 py-12"
    >
      <GlassPanel className="motion-enter flex w-full max-w-sm flex-col gap-6 rounded-xl p-6 sm:p-8">
        <header className="flex flex-col gap-1">
          <p
            translate="no"
            className="font-mono text-sm tracking-wide text-muted-foreground"
          >
            snook
          </p>
          <h1 className="text-xl font-semibold text-balance">{title}</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </header>
        {children}
      </GlassPanel>
    </main>
  )
}
