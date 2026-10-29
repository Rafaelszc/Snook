import { useNavigate } from "react-router"

import { Notice } from "@/components/surfaces/Notice"
import { Button } from "@/components/ui/button"

import { MESSAGES } from "./messages"
import { useCancelSplit } from "./useSplit"

export const backlogPath = (meetingId: string) =>
  `/meetings/${meetingId}/backlog`

// Só com backlog gravado; volta à revisão sem regenerar (`transcript-split` 45).
export function CancelSplitButton({
  meetingId,
  disabled,
}: {
  meetingId: string
  disabled?: boolean
}) {
  const navigate = useNavigate()
  const cancel = useCancelSplit(meetingId)
  return (
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <Button
        variant="secondary"
        disabled={disabled || cancel.isPending}
        aria-describedby="split-cancel-hint"
        onClick={() =>
          cancel.mutate(undefined, {
            onSuccess: () => navigate(backlogPath(meetingId)),
          })
        }
      >
        {cancel.isPending ? MESSAGES.canceling : MESSAGES.cancel}
      </Button>
      <p id="split-cancel-hint" className="text-sm text-ink-muted">
        {MESSAGES.cancelHint}
      </p>
      {cancel.error ? (
        <Notice variant="error">{cancel.error.message}</Notice>
      ) : null}
    </div>
  )
}
