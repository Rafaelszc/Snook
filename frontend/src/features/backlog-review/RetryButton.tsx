import { RotateCcw } from "lucide-react"

import { ConfirmDialog } from "@/components/surfaces/ConfirmDialog"
import { Notice } from "@/components/surfaces/Notice"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

import { MESSAGES } from "./messages"
import { useMeetingMutation } from "./useBacklog"

// "Tentar novamente" de `meetings` com o aviso de perda das edições (`backlog-review` 46; `meetings` 42).
export function RetryButton({ meetingId }: { meetingId: string }) {
  const retry = useMeetingMutation(meetingId, () =>
    api.post(`/meetings/${meetingId}/retry`)
  )
  return (
    <div className="flex flex-col gap-2">
      <ConfirmDialog
        trigger={
          <Button disabled={retry.isPending} className="self-start">
            <RotateCcw aria-hidden="true" />
            {retry.isPending ? MESSAGES.retrying : MESSAGES.retry}
          </Button>
        }
        title={MESSAGES.retryTitle}
        description={MESSAGES.retryDescription}
        confirm={MESSAGES.retryConfirm}
        onConfirm={() => retry.mutate(undefined)}
      />
      {retry.error ? (
        <Notice variant="error">{retry.error.message}</Notice>
      ) : null}
    </div>
  )
}
