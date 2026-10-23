import { useId, type ChangeEventHandler } from "react"

import { cn } from "cn"

interface ModelSelectProps {
  label: string
  value: string
  models: string[]
  hint?: string
  error?: string
  onChange: ChangeEventHandler<HTMLSelectElement>
}

// Select nativo (teclado e leitor de tela de graça); o valor atual sempre é uma opção.
export function ModelSelect({
  label,
  value,
  models,
  hint,
  error,
  onChange,
}: ModelSelectProps) {
  const id = useId()
  const describedBy = `${id}-${error ? "error" : "hint"}`
  const options = value && !models.includes(value) ? [value, ...models] : models

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <select
        id={id}
        name="model"
        value={value}
        onChange={onChange}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? describedBy : undefined}
        className={cn(
          "h-10 w-full min-w-0 rounded-lg border border-input bg-background px-3 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 sm:text-sm dark:bg-input/30"
        )}
      >
        {options.map((model) => (
          <option key={model} value={model}>
            {model}
          </option>
        ))}
      </select>
      {error ? (
        <p id={describedBy} className="text-sm text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={describedBy} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
