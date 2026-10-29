import { ConfirmDialog } from "@/components/surfaces/ConfirmDialog"
import { EmptyState } from "@/components/surfaces/EmptyState"
import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { Notice } from "@/components/surfaces/Notice"
import { PageHeader } from "@/components/surfaces/PageHeader"
import { Skeleton, SkeletonGroup } from "@/components/surfaces/Skeleton"
import { StatusBadge, type Status } from "@/components/surfaces/StatusBadge"
import { ThemeToggle } from "@/components/surfaces/ThemeToggle"
import { Button } from "@/components/ui/button"

const STATUSES: Status[] = [
  "pending",
  "processing",
  "transcribed",
  "needs_split",
  "generating",
  "done",
  "failed",
]

// Tabela "Tokens" do ADR-0024 (cores).
const TOKENS = [
  "canvas",
  "surface",
  "sunken",
  "hairline",
  "ink",
  "ink-muted",
  "input",
  "signal",
  "signal-ink",
  "signal-soft",
  "done",
  "warn",
  "warn-soft",
  "failed",
  "failed-soft",
]

const VARIANTS = ["primary", "accent", "secondary", "ghost", "danger"] as const

function Section({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section
      aria-labelledby={id}
      className="flex flex-col gap-4 border-t border-hairline pt-6"
    >
      <h2 id={id} className="text-lg font-semibold">
        {title}
      </h2>
      {children}
    </section>
  )
}

// Só em desenvolvimento (routes.tsx). No máximo 3 tamanhos de texto: sm, lg, 2xl.
export function SamplePage() {
  return (
    <div className="mx-auto flex w-full max-w-shell flex-col gap-8 p-4">
      <PageHeader
        title="Componentes"
        description="Amostra da direção Ata (ADR-0024)."
        actions={<ThemeToggle />}
      />

      <Section id="sample-tokens" title="Tokens">
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
          {TOKENS.map((token) => (
            <li key={token} className="flex flex-col gap-1">
              <span
                aria-hidden="true"
                className="h-10 rounded-sm border border-hairline"
                style={{ background: `var(--${token})` }}
              />
              <span translate="no" className="font-mono text-sm tabular-nums">
                {token}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="sample-buttons" title="Button">
        <div className="flex flex-wrap gap-2">
          {VARIANTS.map((variant) => (
            <Button key={variant} variant={variant}>
              {variant}
            </Button>
          ))}
        </div>
        <div>
          <ConfirmDialog
            trigger={<Button variant="secondary">Abrir diálogo</Button>}
            title="Excluir reunião?"
            description="Diálogo opaco sobre DialogSurface."
            confirm="Excluir"
            destructive
            onConfirm={() => {}}
          />
        </div>
      </Section>

      <Section id="sample-notice" title="Notice">
        <div className="flex flex-col gap-3">
          <Notice variant="info">Informação sobre o processamento.</Notice>
          <Notice variant="warn">A Transcrição precisa ser dividida.</Notice>
          <Notice variant="error">Não foi possível salvar.</Notice>
          <Notice variant="consent">Aviso de consentimento.</Notice>
        </div>
      </Section>

      <Section id="sample-status" title="Status">
        <ul aria-label="Status" className="flex flex-wrap gap-2">
          {STATUSES.map((status) => (
            <li key={status}>
              <StatusBadge status={status} />
            </li>
          ))}
        </ul>
      </Section>

      <Section id="sample-loading" title="Skeleton e EmptyState">
        <SkeletonGroup label="Carregando amostra…">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-64" />
        </SkeletonGroup>
        <EmptyState
          title="Nenhuma reunião"
          description="Envie uma gravação para começar."
          action={<Button variant="accent">Enviar gravação</Button>}
        />
      </Section>

      <Section id="sample-glass" title="Painel da gravação">
        <div className="rounded-lg bg-signal p-6">
          <GlassPanel className="rounded-lg p-4">
            <p className="text-sm">
              Vidro só no painel flutuante da gravação, com fallback opaco.
            </p>
          </GlassPanel>
        </div>
      </Section>
    </div>
  )
}
