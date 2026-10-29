import type { ReactNode } from "react"
import { AlertDialog } from "radix-ui"

import { Button } from "@/components/ui/button"

import { DialogSurface } from "./DialogSurface"
import { CONFIRM_CANCEL } from "./messages"

interface ConfirmDialogProps {
  trigger?: ReactNode
  title: string
  description: string
  confirm: string
  destructive?: boolean
  // Sem `trigger`: diálogo controlado por `open`/`onOpenChange`.
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children?: ReactNode
  onConfirm: () => void
}

// Diálogo opaco (ADR-0024, "Vidro"): DialogSurface sobre --scrim.
export function ConfirmDialog({
  trigger,
  title,
  description,
  confirm,
  destructive,
  open,
  onOpenChange,
  children,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger ? (
        <AlertDialog.Trigger asChild>{trigger}</AlertDialog.Trigger>
      ) : null}
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="motion-fade-in fixed inset-0 z-50 bg-scrim" />
        <AlertDialog.Content asChild>
          <DialogSurface className="motion-enter fixed top-1/2 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col gap-4 p-6">
            <AlertDialog.Title className="text-base font-semibold">
              {title}
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-muted-foreground">
              {description}
            </AlertDialog.Description>
            {children}
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <AlertDialog.Cancel asChild>
                <Button variant="secondary">{CONFIRM_CANCEL}</Button>
              </AlertDialog.Cancel>
              <AlertDialog.Action asChild>
                <Button
                  variant={destructive ? "danger" : "primary"}
                  onClick={onConfirm}
                >
                  {confirm}
                </Button>
              </AlertDialog.Action>
            </div>
          </DialogSurface>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
