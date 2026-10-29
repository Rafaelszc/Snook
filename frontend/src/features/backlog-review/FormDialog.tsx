import { Dialog } from "radix-ui"
import type { FormEvent, ReactNode } from "react"

import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { Button } from "@/components/ui/button"

import { MESSAGES } from "./messages"

interface FormDialogProps {
  trigger: ReactNode
  title: string
  description?: string
  confirm: string
  pending?: boolean
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: () => void
  children: ReactNode
}

// Diálogo com formulário, sobre `GlassPanel` (NFR-06: um vidro aberto por vez).
export function FormDialog({
  trigger,
  title,
  description,
  confirm,
  pending,
  open,
  onOpenChange,
  onSubmit,
  children,
}: FormDialogProps) {
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit()
  }
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="motion-fade-in fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content
          asChild
          {...(description ? {} : { "aria-describedby": undefined })}
        >
          <GlassPanel className="motion-enter fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-xl p-6">
            <form onSubmit={submit} className="flex flex-col gap-4">
              <Dialog.Title className="text-base font-semibold">
                {title}
              </Dialog.Title>
              {description ? (
                <Dialog.Description className="text-sm text-muted-foreground">
                  {description}
                </Dialog.Description>
              ) : null}
              {children}
              <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <Dialog.Close asChild>
                  <Button type="button" variant="secondary">
                    {MESSAGES.cancel}
                  </Button>
                </Dialog.Close>
                <Button type="submit" disabled={pending}>
                  {pending ? MESSAGES.saving : confirm}
                </Button>
              </div>
            </form>
          </GlassPanel>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
