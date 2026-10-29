import type { ReactNode } from "react"
import { cn } from "cn"

import { useReducedMotion } from "@/lib/ui/useReducedMotion"

// Bloco de carregamento: --sunken, --r-4, respiração lenta de opacidade (ADR-0024).
// Parado com prefers-reduced-motion (hook e motion.css concordam).
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  const reduced = useReducedMotion()

  return (
    <div
      aria-hidden="true"
      data-slot="skeleton"
      className={cn(
        "rounded-sm bg-sunken",
        !reduced && "motion-breathe",
        className
      )}
      {...props}
    />
  )
}

// Contêiner de carregamento: anuncia o rótulo e marca aria-busy.
function SkeletonGroup({
  label,
  children,
  className,
  ...props
}: { label: string; children: ReactNode } & Omit<
  React.ComponentProps<"div">,
  "children" | "role"
>) {
  return (
    <div
      role="status"
      aria-busy="true"
      className={cn("flex flex-col gap-3", className)}
      {...props}
    >
      <span className="sr-only">{label}</span>
      {children}
    </div>
  )
}

export { Skeleton, SkeletonGroup }
