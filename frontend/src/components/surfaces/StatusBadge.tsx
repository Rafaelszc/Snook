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
const VISUAL: Record<Status, { icon: LucideIcon; color: string }> = {
  pending: { icon: Clock, color: "text-status-pending" },
  processing: { icon: Loader, color: "text-status-processing" },
  transcribed: { icon: CheckCheck, color: "text-highlight" },
  needs_split: { icon: Scissors, color: "text-highlight" },
  generating: { icon: Sparkles, color: "text-status-processing" },
  done: { icon: CircleCheck, color: "text-status-done" },
  failed: { icon: CircleAlert, color: "text-status-failed" },
}

// role="status" é uma região aria-live polite: o leitor de tela anuncia a troca de texto.
function StatusBadge({
  status,
  className,
  ...props
}: { status: Status } & Omit<React.ComponentProps<"span">, "children">) {
  const { icon: Icon, color } = VISUAL[status]

  return (
    <span
      role="status"
      aria-live="polite"
      data-slot="status-badge"
      data-status={status}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border px-2 py-0.5 text-xs font-medium",
        color,
        className
      )}
      {...props}
    >
      <Icon aria-hidden="true" className="size-3.5 shrink-0" />
      {STATUS_LABELS[status]}
    </span>
  )
}

export { StatusBadge }
