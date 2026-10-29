import * as React from "react"
import { cn } from "cn"

// Superfície opaca de diálogo (ADR-0024, "Vidro"): --surface, --r-10, --overlay-shadow,
// sem backdrop-filter. O overlay do diálogo usa bg-scrim.
function DialogSurface({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-surface"
      className={cn("rounded-lg bg-surface text-ink shadow-overlay", className)}
      {...props}
    />
  )
}

export { DialogSurface }
