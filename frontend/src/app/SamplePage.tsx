import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { StatusBadge, type Status } from "@/components/surfaces/StatusBadge"

const STATUSES: Status[] = [
  "pending",
  "processing",
  "transcribed",
  "needs_split",
  "generating",
  "done",
  "failed",
]

const TOKENS = [
  "background",
  "foreground",
  "card",
  "muted",
  "primary",
  "highlight",
  "destructive",
  "border",
]

// Só em desenvolvimento (routes.tsx). No máximo 3 tamanhos de texto: sm, base, xl.
export function SamplePage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 p-4">
      <h1 className="text-xl font-semibold">Componentes</h1>

      <section aria-labelledby="sample-tokens" className="flex flex-col gap-3">
        <h2 id="sample-tokens" className="text-base font-semibold">
          Tokens
        </h2>
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {TOKENS.map((token) => (
            <li key={token} className="flex flex-col gap-1">
              <span
                aria-hidden="true"
                className="h-10 rounded-md border border-border"
                style={{ background: `var(--${token})` }}
              />
              <span className="font-mono text-sm tabular-nums">{token}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="sample-glass" className="flex flex-col gap-3">
        <h2 id="sample-glass" className="text-base font-semibold">
          GlassPanel
        </h2>
        <div className="rounded-xl bg-gradient-to-br from-highlight to-foreground p-6">
          <GlassPanel className="rounded-lg p-4">
            <p className="text-sm">
              Vidro só em superfície flutuante, com fallback opaco.
            </p>
          </GlassPanel>
        </div>
      </section>

      <section aria-labelledby="sample-status" className="flex flex-col gap-3">
        <h2 id="sample-status" className="text-base font-semibold">
          Status
        </h2>
        <ul aria-label="Status" className="flex flex-wrap gap-2">
          {STATUSES.map((status) => (
            <li key={status}>
              <StatusBadge status={status} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
