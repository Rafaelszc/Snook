import * as React from "react"
import { cn } from "cn"

// jsdom e navegadores antigos não têm CSS.supports("backdrop-filter").
function supportsBackdropFilter(): boolean {
  return (
    typeof CSS !== "undefined" && CSS.supports("backdrop-filter", "blur(1px)")
  )
}

// Única superfície com vidro (ADR-0022); fallback opaco em glass.css.
function GlassPanel({ className, ...props }: React.ComponentProps<"div">) {
  const [glass] = React.useState(supportsBackdropFilter)

  return (
    <div
      data-slot="glass-panel"
      className={cn("glass", !glass && "glass-opaque", className)}
      {...props}
    />
  )
}

export { GlassPanel }
