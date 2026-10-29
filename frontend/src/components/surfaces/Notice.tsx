import type { ReactNode } from "react"
import {
  CircleAlert,
  Info,
  ShieldCheck,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react"
import { cn } from "cn"

type NoticeVariant = "info" | "warn" | "error" | "consent"

// ADR-0024, "Componentes": alerta de bloco ou de página. Erro de campo fica no FormField.
const VISUAL: Record<
  NoticeVariant,
  { icon: LucideIcon; box: string; iconColor: string; role?: string }
> = {
  info: {
    icon: Info,
    box: "border-signal bg-signal-soft",
    iconColor: "text-signal",
    role: "status",
  },
  warn: {
    icon: TriangleAlert,
    box: "border-warn bg-warn-soft",
    iconColor: "text-warn",
    role: "status",
  },
  error: {
    icon: CircleAlert,
    box: "border-failed bg-failed-soft",
    iconColor: "text-failed",
    role: "alert",
  },
  // Sem região viva: o aviso de consentimento é texto fixo da tela.
  consent: {
    icon: ShieldCheck,
    box: "border-ink-muted bg-sunken",
    iconColor: "text-ink-muted",
  },
}

function Notice({
  variant,
  children,
  className,
  ...props
}: {
  variant: NoticeVariant
  children: ReactNode
} & Omit<React.ComponentProps<"div">, "children" | "role">) {
  const { icon: Icon, box, iconColor, role } = VISUAL[variant]

  return (
    <div
      role={role}
      data-slot="notice"
      data-variant={variant}
      className={cn(
        "flex items-start gap-3 border-l-2 px-4 py-3 text-sm text-ink",
        box,
        className
      )}
      {...props}
    >
      <Icon
        aria-hidden="true"
        className={cn("mt-1 size-4 shrink-0", iconColor)}
      />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

export { Notice, type NoticeVariant }
