import { Pencil } from "lucide-react"
import { cn } from "cn"
import { type ReactNode, useId, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

import { fieldError } from "./fieldError"
import { MESSAGES } from "./messages"

export const TEXTAREA =
  "min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive sm:text-sm dark:bg-input/30"

interface EditableFieldProps {
  // Nome acessível do campo ("Editar <label>").
  label: string
  value: string
  // Chave de `error.fields` na resposta 422.
  field: string
  onSave: (value: string) => Promise<unknown>
  readOnly?: boolean
  multiline?: boolean
  mono?: boolean
  maxLength?: number
  // Aviso mostrado enquanto digita, antes de salvar (`backlog-review` 41).
  notice?: (draft: string) => string | undefined
  // Conteúdo em leitura; padrão: `value`.
  children?: ReactNode
  className?: string
}

// Edição no lugar (`backlog-review` 40). Enter salva (Ctrl+Enter no texto longo), Esc cancela.
export function EditableField({
  label,
  value,
  field,
  onSave,
  readOnly,
  multiline,
  mono,
  maxLength,
  notice,
  children,
  className,
}: EditableFieldProps) {
  const id = useId()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const [error, setError] = useState<string>()
  const [saving, setSaving] = useState(false)
  const editRef = useRef<HTMLButtonElement>(null)

  const close = () => {
    setEditing(false)
    setError(undefined)
    requestAnimationFrame(() => editRef.current?.focus())
  }

  const save = async () => {
    if (draft === value) return close()
    setSaving(true)
    try {
      await onSave(draft)
      close()
    } catch (cause) {
      setError(fieldError(cause, field))
    } finally {
      setSaving(false)
    }
  }

  if (!editing) {
    return (
      <div className={cn("group flex items-start gap-1", className)}>
        <div
          className={cn(
            "min-w-0 flex-1 break-words",
            mono && "font-mono tabular-nums"
          )}
        >
          {children ?? value}
        </div>
        {readOnly ? null : (
          <Button
            ref={editRef}
            variant="ghost"
            size="icon-sm"
            aria-label={MESSAGES.edit(label)}
            className="shrink-0 text-muted-foreground"
            onClick={() => {
              setDraft(value)
              setEditing(true)
            }}
          >
            <Pencil aria-hidden="true" />
          </Button>
        )}
      </div>
    )
  }

  const hint = notice?.(draft)
  const errorId = `${id}-error`
  const hintId = `${id}-hint`
  const describedBy =
    [error && errorId, hint && hintId].filter(Boolean).join(" ") || undefined
  const common = {
    id,
    "aria-label": label,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy,
    value: draft,
    maxLength,
    autoFocus: true,
    disabled: saving,
    onChange: (event: { target: { value: string } }) =>
      setDraft(event.target.value),
    onKeyDown: (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault()
        close()
      }
      if (
        event.key === "Enter" &&
        (!multiline || event.ctrlKey || event.metaKey)
      ) {
        event.preventDefault()
        void save()
      }
    },
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {multiline ? (
        <textarea {...common} className={TEXTAREA} />
      ) : (
        <Input
          {...common}
          className={mono ? "font-mono tabular-nums" : undefined}
        />
      )}
      {hint ? (
        <p id={hintId} role="status" className="text-sm text-highlight">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button disabled={saving} onClick={() => void save()}>
          {saving ? MESSAGES.saving : MESSAGES.save}
        </Button>
        <Button variant="secondary" disabled={saving} onClick={close}>
          {MESSAGES.cancel}
        </Button>
      </div>
    </div>
  )
}

interface SelectFieldProps {
  label: string
  value: string
  field: string
  options: readonly { value: string; label: string }[]
  onSave: (value: string) => Promise<unknown>
  readOnly?: boolean
  // Texto em leitura; padrão: rótulo da opção.
  display?: string
  mono?: boolean
}

// Lista nativa: troca salva na hora; erro da API embaixo (`backlog-review` 40).
export function SelectField({
  label,
  value,
  field,
  options,
  onSave,
  readOnly,
  display,
  mono,
}: SelectFieldProps) {
  const id = useId()
  const [error, setError] = useState<string>()
  const [saving, setSaving] = useState(false)
  const shown =
    display ?? options.find((o) => o.value === value)?.label ?? value

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm text-muted-foreground">
        {label}
      </label>
      {readOnly ? (
        <span
          id={id}
          className={cn("text-sm", mono && "font-mono tabular-nums")}
        >
          {shown}
        </span>
      ) : (
        <select
          id={id}
          value={value}
          disabled={saving}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          className={cn(
            "h-9 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive dark:bg-input/30",
            mono && "font-mono tabular-nums"
          )}
          onChange={async (event) => {
            setSaving(true)
            setError(undefined)
            try {
              await onSave(event.target.value)
            } catch (cause) {
              setError(fieldError(cause, field))
            } finally {
              setSaving(false)
            }
          }}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  )
}
