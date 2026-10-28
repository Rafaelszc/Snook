import { AlertDialog } from "radix-ui"

import { GlassPanel } from "@/components/surfaces/GlassPanel"
import { Button } from "@/components/ui/button"

import type { Browser } from "./capture/interfaces"
import { MESSAGES } from "./messages"
import type { Source } from "./useRecordingSession"

const COPY = {
  display: { description: MESSAGES.missingDisplay, confirm: MESSAGES.micOnly },
  mic: { description: MESSAGES.missingMic, confirm: MESSAGES.displayOnly },
} as const

// Aberto enquanto falta uma fonte; nada grava antes da escolha (`screen-recording` 4, 5).
export function SourceWarningDialog({
  missing,
  browser,
  onConfirm,
  onCancel,
}: {
  missing: Source
  browser: Browser
  onConfirm: () => void
  onCancel: () => void
}) {
  const copy = COPY[missing]
  const description =
    missing === "display" && browser === "firefox"
      ? MESSAGES.missingDisplayFirefox
      : copy.description
  return (
    <AlertDialog.Root open onOpenChange={(open) => !open && onCancel()}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="motion-fade-in fixed inset-0 z-50 bg-black/40" />
        <AlertDialog.Content asChild>
          <GlassPanel className="motion-enter fixed top-1/2 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-xl p-6">
            <AlertDialog.Title className="text-base font-semibold">
              {MESSAGES.missingTitle}
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-muted-foreground">
              {description}
            </AlertDialog.Description>
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button variant="outline" onClick={onCancel}>
                {MESSAGES.cancel}
              </Button>
              <Button onClick={onConfirm}>{copy.confirm}</Button>
            </div>
          </GlassPanel>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
