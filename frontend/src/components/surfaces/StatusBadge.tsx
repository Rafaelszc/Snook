import {
  CheckCheck,
  CircleAlert,
  CircleCheck,
  Clock,
  Loader,
  Scissors,
  Sparkles,
  type LucideIcon,
} from "lucide-react"
import { cn } from "cn"

import { STATUS_LABELS, type Status } from "./messages"

export type { Status }

// Texto e ícone sempre presentes: a cor nunca carrega o estado sozinha.
// Cor do ícone por estado; rótulo em --ink, exceto failed (ADR-0024, "Estados").
const VISUAL: Record<Status, { icon: LucideIcon; color: string }> = {
  pending: { icon: Clock, color: "text-ink-muted" },
  processing: { icon: Loader, color: "text-signal" },
  transcribed: { icon: CheckCheck, color: "text-ink" },
  needs_split: { icon: Scissors, color: "text-warn" },
  generating: { icon: Sparkles, color: "text-signal" },
  done: { icon: CircleCheck, color: "text-done" },
  failed: { icon: CircleAlert, color: "text-failed" },
}

// role="status" é uma região aria-live polite: o leitor de tela anuncia a troca de texto.
function StatusBadge({
  status,
  className,
  ...props
}: { status: Status } & Omit<React.ComponentProps<"span">, "children">) {
  const { icon: Icon, color } = VISUAL[status]
  const label = status === "failed" ? "text-failed" : "text-ink"

  return (
    <span
      role="status"
      aria-live="polite"
      data-slot="status-badge"
      data-status={status}
      className={cn(
        "inline-flex items-center gap-2 text-sm font-medium whitespace-nowrap",
        label,
        className
      )}
      {...props}
    >
      <Icon aria-hidden="true" className={cn("size-4 shrink-0", color)} />
      {STATUS_LABELS[status]}
    </span>
  )
}

export { StatusBadge }
