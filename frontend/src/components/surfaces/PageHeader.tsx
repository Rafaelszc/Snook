import type { ReactNode } from "react"
import { cn } from "cn"

// Cabeçalho de página (ADR-0024): título serif, descrição em --ink-muted, ações à direita. Sem card.
function PageHeader({
  title,
  description,
  actions,
  className,
  ...props
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
} & Omit<React.ComponentProps<"header">, "title" | "children">) {
  return (
    <header
      data-slot="page-header"
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between",
        className
      )}
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-balance text-ink">
          {title}
        </h1>
        {description ? (
          <p className="text-sm text-pretty text-ink-muted">{description}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      ) : null}
    </header>
  )
}

export { PageHeader }
