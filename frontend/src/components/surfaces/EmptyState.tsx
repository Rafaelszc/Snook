import type { ReactNode } from "react"
import { cn } from "cn"

// Estado vazio único (ADR-0024): título, descrição e ação opcional. Sem card.
function EmptyState({
  title,
  description,
  action,
  className,
  ...props
}: {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
} & Omit<React.ComponentProps<"div">, "title" | "children">) {
  return (
    <div
      data-slot="empty-state"
      className={cn(
        "flex flex-col items-start gap-3 border-t border-hairline py-8",
        className
      )}
      {...props}
    >
      <p className="font-heading text-lg text-ink">{title}</p>
      {description ? (
        <p className="text-sm text-pretty text-ink-muted">{description}</p>
      ) : null}
      {action ? <div className="pt-2">{action}</div> : null}
    </div>
  )
}

export { EmptyState }
