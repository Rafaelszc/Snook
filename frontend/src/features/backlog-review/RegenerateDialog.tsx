import { RefreshCw } from "lucide-react"
import { AlertDialog } from "radix-ui"
import { useState } from "react"
import { useNavigate } from "react-router"

import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api/client"

import type { RegenerateMode } from "./api"
import { MESSAGES } from "./messages"
import { useIsSplit, useMeetingMutation } from "./useBacklog"

// Avisa que as edições se perdem; dividida, oferece os dois modos (`backlog-review` 44).
export function RegenerateDialog({ meetingId }: { meetingId: string }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const split = useIsSplit(meetingId, open)
  const regenerate = useMeetingMutation(meetingId, (mode: RegenerateMode) =>
    api.post<{ status: string }>(`/meetings/${meetingId}/regenerate`, { mode })
  )

  const run = (mode: RegenerateMode) =>
    regenerate.mutate(mode, {
      onSuccess: ({ status }) => {
        setOpen(false)
        // Reajustar: a Reunião volta para a tela de divisão (`transcript-split`).
        if (status === "needs_split") navigate(`/meetings/${meetingId}/split`)
      },
    })

  return (
    <AlertDialog.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        regenerate.reset()
      }}
    >
      <AlertDialog.Trigger asChild>
        <Button>
          <RefreshCw aria-hidden="true" />
          {MESSAGES.regenerate}
        </Button>
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="motion-fade-in fixed inset-0 z-50 bg-black/40" />
        <AlertDialog.Content asChild>
          <GlassPanel className="motion-enter fixed top-1/2 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-xl p-6">
            <AlertDialog.Title className="text-base font-semibold">
              {MESSAGES.regenerateTitle}
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-muted-foreground">
              {MESSAGES.regenerateDescription}
            </AlertDialog.Description>
            {split.data ? (
              <p className="text-sm">{MESSAGES.regenerateSplit}</p>
            ) : null}
            {split.isPending ? (
              <p role="status" className="text-sm text-muted-foreground">
                {MESSAGES.checkingSplit}
              </p>
            ) : null}
            {(regenerate.error ?? split.error) ? (
              <p role="alert" className="text-sm text-destructive">
                {(regenerate.error ?? split.error)?.message}
              </p>
            ) : null}
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <AlertDialog.Cancel asChild>
                <Button variant="outline">{MESSAGES.cancel}</Button>
              </AlertDialog.Cancel>
              {split.data ? (
                <>
                  <Button
                    variant="outline"
                    disabled={regenerate.isPending}
                    onClick={() => run("adjust_cuts")}
                  >
                    {MESSAGES.adjustCuts}
                  </Button>
                  <Button
                    disabled={regenerate.isPending}
                    onClick={() => run("same_cuts")}
                  >
                    {MESSAGES.sameCuts}
                  </Button>
                </>
              ) : (
                <Button
                  disabled={
                    regenerate.isPending || split.isPending || split.isError
                  }
                  onClick={() => run("same_cuts")}
                >
                  {regenerate.isPending
                    ? MESSAGES.regenerating
                    : MESSAGES.regenerate}
                </Button>
              )}
            </div>
          </GlassPanel>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
