import { useId } from "react"
import { Circle, CircleCheck, CircleDot, type LucideIcon } from "lucide-react"
import { cn } from "cn"

import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"

import type { ConfigState, LlmConfig } from "./api"
import { MESSAGES, PROVIDER_LABELS, STATE_LABELS } from "./messages"
import { ProviderForm } from "./ProviderForm"
import { useLlmConfigs } from "./useLlmConfigs"

// Texto e ícone sempre juntos: a cor nunca carrega o estado sozinha.
const STATE_VISUAL: Record<ConfigState, { icon: LucideIcon; color: string }> = {
  not_configured: { icon: Circle, color: "text-ink-muted" },
  configured: { icon: CircleDot, color: "text-ink" },
  active: { icon: CircleCheck, color: "text-done" },
}

function StateLabel({ state }: { state: ConfigState }) {
  const { icon: Icon, color } = STATE_VISUAL[state]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 text-sm font-medium",
        color
      )}
    >
      <Icon aria-hidden="true" className="size-4 shrink-0" />
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
          <dt className="text-ink-muted">{term}</dt>
          <dd
            translate="no"
            title={value}
            className="truncate font-mono tabular-nums"
          >
            {value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

// Provedor como linha com régua --hairline, sem card (ADR-0024, "Profundidade").
// Em tela larga, resumo à esquerda e formulário à direita.
function ProviderSection({ config }: { config: LlmConfig }) {
  const headingId = useId()
  return (
    <section
      aria-labelledby={headingId}
      data-state={config.state}
      className="grid gap-6 py-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] lg:gap-12"
    >
      <div className="flex min-w-0 flex-col gap-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h2
            id={headingId}
            className="font-heading text-base font-semibold text-ink"
          >
            {PROVIDER_LABELS[config.provider]}
          </h2>
          <StateLabel state={config.state} />
        </header>
        {config.state === "not_configured" ? null : <Summary config={config} />}
      </div>
      <ProviderForm config={config} />
    </section>
  )
}

// Tamanhos de texto: sm, base, 2xl.
export function SettingsPage() {
  const { data, error, isPending } = useLlmConfigs()

  return (
    <div className="flex flex-col gap-8">
      <PageHeader title={MESSAGES.title} description={MESSAGES.description} />
      {error ? (
        <Notice variant="error">{error.message || MESSAGES.loadError}</Notice>
      ) : isPending ? (
        <SkeletonGroup label={MESSAGES.loading}>
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </SkeletonGroup>
      ) : (
        // Régua forte em --ink no topo da lista (ADR-0024).
        <div className="divide-y divide-hairline border-t border-b border-t-ink border-b-hairline">
          {data.map((config) => (
            <ProviderSection key={config.provider} config={config} />
          ))}
        </div>
      )}
    </div>
  )
}
