import { Trash2 } from "lucide-react"
import { useNavigate } from "react-router"

import { Button } from "@/components/ui/button"

import { ConfirmDialog } from "@/components/surfaces/ConfirmDialog"
import { MESSAGES } from "./messages"
import { useDeleteMeeting } from "./useMeetings"

// Confirma e avisa que áudio e backlog serão apagados (`meetings` 43).
export function DeleteMeetingDialog({ meetingId }: { meetingId: string }) {
  const navigate = useNavigate()
  const remove = useDeleteMeeting(meetingId)

  return (
    <div className="flex flex-col gap-2">
      <ConfirmDialog
        trigger={
          <Button variant="ghost" disabled={remove.isPending}>
            <Trash2 aria-hidden="true" />
            {MESSAGES.remove}
          </Button>
        }
        title={MESSAGES.removeTitle}
        description={MESSAGES.removeDescription}
        confirm={MESSAGES.removeConfirm}
        destructive
        onConfirm={() =>
          remove.mutate(undefined, {
            onSuccess: () => navigate("/", { replace: true }),
          })
        }
      />
      {remove.error ? (
        <p role="alert" className="text-sm text-destructive">
          {remove.error.message}
        </p>
      ) : null}
    </div>
  )
}
