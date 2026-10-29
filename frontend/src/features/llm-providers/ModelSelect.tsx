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
    <div className="flex flex-col gap-2">
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
          "h-10 w-full min-w-0 rounded-md border border-input bg-surface px-3 text-base text-ink outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50 aria-invalid:border-failed sm:text-sm"
        )}
      >
        {options.map((model) => (
          <option key={model} value={model}>
            {model}
          </option>
        ))}
      </select>
      {error ? (
        <p id={describedBy} className="text-sm text-failed">
          {error}
        </p>
      ) : hint ? (
        <p id={describedBy} className="text-sm text-ink-muted">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
