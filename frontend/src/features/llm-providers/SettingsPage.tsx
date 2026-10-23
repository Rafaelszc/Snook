import { useId } from "react"
import { Circle, CircleCheck, CircleDot, type LucideIcon } from "lucide-react"
import { cn } from "cn"

import type { ConfigState, LlmConfig } from "./api"
import { MESSAGES, PROVIDER_LABELS, STATE_LABELS } from "./messages"
import { ProviderForm } from "./ProviderForm"
import { useLlmConfigs } from "./useLlmConfigs"

// Texto e ícone sempre juntos: a cor nunca carrega o estado sozinha.
const STATE_VISUAL: Record<ConfigState, { icon: LucideIcon; color: string }> = {
  not_configured: { icon: Circle, color: "text-muted-foreground" },
  configured: { icon: CircleDot, color: "text-foreground" },
  active: { icon: CircleCheck, color: "text-status-done" },
}

function StateLabel({ state }: { state: ConfigState }) {
  const { icon: Icon, color } = STATE_VISUAL[state]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-sm font-medium",
        color
      )}
    >
      <Icon aria-hidden="true" className="size-3.5 shrink-0" />
      {STATE_LABELS[state]}
    </span>
  )
}

// Resumo do que está salvo: só máscara da chave; URL do Ollama inteira (llm-providers 3, 4).
function Summary({ config }: { config: LlmConfig }) {
  const usesUrl = config.provider === "ollama"
  const secret = usesUrl ? config.base_url : config.key_mask
  const rows = [
    {
      term: usesUrl ? MESSAGES.url : MESSAGES.key,
      value: secret ?? MESSAGES.notSet,
    },
    { term: MESSAGES.model, value: config.model ?? MESSAGES.notSet },
    {
      term: MESSAGES.contextWindow,
      value:
        config.context_window === null
          ? MESSAGES.notSet
          : MESSAGES.tokens(config.context_window),
    },
  ]
  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
      {rows.map(({ term, value }) => (
        <div key={term} className="contents">
          <dt className="text-muted-foreground">{term}</dt>
          <dd translate="no" className="truncate font-mono tabular-nums">
            {value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function ProviderSection({ config }: { config: LlmConfig }) {
  const headingId = useId()
  return (
    <section
      aria-labelledby={headingId}
      data-state={config.state}
      className={cn(
        "flex flex-col gap-5 rounded-xl border bg-card p-5 text-card-foreground sm:p-6",
        config.state === "active" ? "border-foreground/40" : "border-border"
      )}
    >
      <header className="flex items-center justify-between gap-3">
        <h2 id={headingId} className="text-base font-semibold">
          {PROVIDER_LABELS[config.provider]}
        </h2>
        <StateLabel state={config.state} />
      </header>
      {config.state === "not_configured" ? null : <Summary config={config} />}
      <ProviderForm config={config} />
    </section>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function SettingsPage() {
  const { data, error, isPending } = useLlmConfigs()

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 py-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-balance">
          {MESSAGES.title}
        </h1>
        <p className="text-sm text-muted-foreground">{MESSAGES.description}</p>
      </header>
      {error ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {error.message || MESSAGES.loadError}
        </p>
      ) : isPending ? (
        <div aria-busy="true" className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="h-72 rounded-xl bg-muted" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.map((config) => (
            <ProviderSection key={config.provider} config={config} />
          ))}
        </div>
      )}
    </div>
  )
}
