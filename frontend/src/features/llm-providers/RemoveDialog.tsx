import { AlertDialog } from "radix-ui"

import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { Button } from "@/components/ui/button"

import { MESSAGES } from "./messages"

interface RemoveDialogProps {
  providerLabel: string
  disabled?: boolean
  onConfirm: () => void
}

// Confirmação antes de chamar a API (llm-providers 37). Vidro só no diálogo (02-architecture.md, "Mapa de superfícies").
export function RemoveDialog({
  providerLabel,
  disabled,
  onConfirm,
}: RemoveDialogProps) {
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>
        <Button variant="ghost" disabled={disabled}>
          {MESSAGES.remove}
        </Button>
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="motion-fade fixed inset-0 z-50 bg-black/40" />
        <AlertDialog.Content asChild>
          <GlassPanel className="motion-enter fixed top-1/2 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-xl p-6">
            <AlertDialog.Title className="text-base font-semibold">
              {MESSAGES.removeTitle(providerLabel)}
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-muted-foreground">
              {MESSAGES.removeDescription}
            </AlertDialog.Description>
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <AlertDialog.Cancel asChild>
                <Button variant="outline">{MESSAGES.cancel}</Button>
              </AlertDialog.Cancel>
              <AlertDialog.Action asChild>
                <Button variant="destructive" onClick={onConfirm}>
                  {MESSAGES.removeConfirm}
                </Button>
              </AlertDialog.Action>
            </div>
          </GlassPanel>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
