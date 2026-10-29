import { Notice } from "../Notice"
import { CONSENT_NOTICE_TEXT } from "./messages"

// Aviso de consentimento (LGPD): só texto, não pede confirmação nem bloqueia (Q71).
// Usado no upload (`meetings`) e na gravação (`screen-recording`).
function ConsentNotice(
  props: Omit<React.ComponentProps<"div">, "children" | "role">
) {
  return (
    <Notice variant="consent" data-testid="consent-notice" {...props}>
      {CONSENT_NOTICE_TEXT}
    </Notice>
  )
}

export { ConsentNotice }
