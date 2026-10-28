import { Trash2 } from "lucide-react"
import { useId, useState } from "react"

import { ConfirmDialog } from "@/components/surfaces/ConfirmDialog"
import { Button } from "@/components/ui/button"

import { MESSAGES } from "./messages"

interface ConfirmDeleteDialogProps {
  // Nome acessível do botão de excluir.
  label: string
  title: string
  description: string
  onConfirm: () => Promise<unknown>
  // Desabilitado com motivo visível no `title` e lido por `aria-describedby`.
  blockedReason?: string
}

// Excluir pede confirmação (`backlog-review` 42).
export function ConfirmDeleteDialog({
  label,
  title,
  description,
  onConfirm,
  blockedReason,
}: ConfirmDeleteDialogProps) {
  const [error, setError] = useState<string>()
  const [pending, setPending] = useState(false)
  const reasonId = useId()

  const button = (
    <Button
      variant="ghost"
      size="icon-sm"
      aria-label={label}
      title={blockedReason ?? label}
      disabled={Boolean(blockedReason) || pending}
      aria-describedby={blockedReason ? reasonId : undefined}
      className="text-muted-foreground"
    >
      <Trash2 aria-hidden="true" />
    </Button>
  )

  return (
    <>
      {blockedReason ? (
        <>
          {button}
          <span id={reasonId} className="sr-only">
            {blockedReason}
          </span>
        </>
      ) : (
        <ConfirmDialog
          trigger={button}
          title={title}
          description={description}
          confirm={MESSAGES.delete}
          destructive
          onConfirm={async () => {
            setPending(true)
            setError(undefined)
            try {
              await onConfirm()
            } catch (cause) {
              setError(cause instanceof Error ? cause.message : String(cause))
            } finally {
              setPending(false)
            }
          }}
        />
      )}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </>
  )
}
