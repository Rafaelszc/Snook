import { Braces, FileDown } from "lucide-react"

import { buttonVariants } from "@/components/ui/button"

import { exportUrl } from "./api"
import { MESSAGES } from "./messages"

// Download direto, mesma origem e cookie de sessão; o servidor manda o anexo (`backlog-review` 45; SEC-12).
export function ExportButtons({ meetingId }: { meetingId: string }) {
  return (
    <>
      <a
        href={exportUrl(meetingId, "md")}
        download
        className={buttonVariants({ variant: "secondary" })}
      >
        <FileDown aria-hidden="true" />
        {MESSAGES.exportMd}
      </a>
      <a
        href={exportUrl(meetingId, "json")}
        download
        className={buttonVariants({ variant: "secondary" })}
      >
        <Braces aria-hidden="true" />
        {MESSAGES.exportJson}
      </a>
    </>
  )
}
