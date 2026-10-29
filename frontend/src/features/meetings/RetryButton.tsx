import { RotateCcw } from "lucide-react"

import { Button } from "@/components/ui/button"

import type { MeetingDetail } from "./api"
import { ConfirmDialog } from "@/components/surfaces/ConfirmDialog"
import { Notice } from "@/components/surfaces/Notice"
import { MESSAGES } from "./messages"
import { useRetryMeeting } from "./useMeetings"

// Só em `failed`. Com backlog gravado, confirma antes: as edições se perdem (`meetings` 42).
export function RetryButton({ meeting }: { meeting: MeetingDetail }) {
  const retry = useRetryMeeting(meeting.id)
  if (meeting.status !== "failed") return null

  const button = (
    <Button
      disabled={retry.isPending}
      onClick={meeting.has_backlog ? undefined : () => retry.mutate()}
    >
      <RotateCcw aria-hidden="true" />
      {retry.isPending ? MESSAGES.retrying : MESSAGES.retry}
    </Button>
  )

  return (
    <div className="flex flex-col gap-2">
      {meeting.has_backlog ? (
        <ConfirmDialog
          trigger={button}
          title={MESSAGES.retryTitle}
          description={MESSAGES.retryDescription}
          confirm={MESSAGES.retryConfirm}
          onConfirm={() => retry.mutate()}
        />
      ) : (
        button
      )}
      {retry.error ? (
        <Notice variant="error">{retry.error.message}</Notice>
      ) : null}
    </div>
  )
}
