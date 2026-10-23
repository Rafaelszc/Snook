import { useId, type ComponentProps } from "react"

import { Input } from "@/components/ui/input"

interface FormFieldProps extends ComponentProps<"input"> {
  label: string
  hint?: string
  error?: string
}

// Rótulo visível, dica e erro ligados ao campo por aria-describedby.
export function FormField({ label, hint, error, ...input }: FormFieldProps) {
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy =
    [error && errorId, hint && hintId].filter(Boolean).join(" ") || undefined

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        {...input}
      />
      {error ? (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
