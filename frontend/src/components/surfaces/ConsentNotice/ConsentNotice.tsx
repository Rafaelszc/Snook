import { ShieldCheck } from "lucide-react"
import { cn } from "cn"

import { CONSENT_NOTICE_TEXT } from "./messages"

// Aviso de consentimento (LGPD): só texto, não pede confirmação nem bloqueia (Q71).
// Usado no upload (`meetings`) e na gravação (`screen-recording`).
function ConsentNotice({
  className,
  ...props
}: Omit<React.ComponentProps<"p">, "children">) {
  return (
    <p
      data-testid="consent-notice"
      className={cn(
        "flex items-start gap-2 text-sm text-muted-foreground",
        className
      )}
      {...props}
    >
      <ShieldCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span>{CONSENT_NOTICE_TEXT}</span>
    </p>
  )
}

export { ConsentNotice }
