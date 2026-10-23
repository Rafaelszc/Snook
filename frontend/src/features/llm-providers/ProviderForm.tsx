import { useId, useState, type ChangeEvent, type FormEvent } from "react"

import { FormField } from "@/components/forms/FormField"
import { Button } from "@/components/ui/button"
import type { ApiError, FieldErrors } from "@/lib/api/errors"

import type { ConfigDraft, LlmConfig } from "./api"
import { MESSAGES, OLLAMA_URL_HINT, PROVIDER_LABELS } from "./messages"
import { ModelSelect } from "./ModelSelect"
import { RemoveDialog } from "./RemoveDialog"
import {
  useActivateConfig,
  useListModels,
  useRemoveConfig,
  useSaveConfig,
  useTestConnection,
} from "./useLlmConfigs"

interface FormValues {
  api_key: string
  base_url: string
  model: string
  context_window: string
}

// Chave nunca vem preenchida; vazio na edição mantém a atual (llm-providers 36).
function initialValues(config: LlmConfig): FormValues {
  return {
    api_key: "",
    base_url: config.base_url ?? "",
    model: config.model ?? config.default_model,
    context_window: String(
      config.context_window ?? config.default_context_window
    ),
  }
}

// Campo vazio fica fora do corpo: o servidor usa o salvo, senão o padrão.
function toDraft(
  values: FormValues,
  usesUrl: boolean
): { draft: ConfigDraft } | { fieldErrors: FieldErrors } {
  const draft: ConfigDraft = {}
  const key = values.api_key.trim()
  const url = values.base_url.trim()
  const model = values.model.trim()
  const window = values.context_window.trim()
  if (!usesUrl && key) draft.api_key = key
  if (usesUrl && url) draft.base_url = url
  if (model) draft.model = model
  if (window) {
    if (!/^\d+$/.test(window) || Number(window) < 1)
      return { fieldErrors: { context_window: MESSAGES.invalidContextWindow } }
    draft.context_window = Number(window)
  }
  return { draft }
}

function errorFields(error: ApiError | null): FieldErrors {
  return error?.fields ?? {}
}

export function ProviderForm({ config }: { config: LlmConfig }) {
  const formId = useId()
  const label = PROVIDER_LABELS[config.provider]
  const usesUrl = config.provider === "ollama"
  const configured = config.state !== "not_configured"

  const test = useTestConnection(config.provider)
  const listModels = useListModels(config.provider)
  const save = useSaveConfig(config.provider)
  const activate = useActivateConfig(config.provider)
  const remove = useRemoveConfig(config.provider)

  const [values, setValues] = useState(() => initialValues(config))
  const [models, setModels] = useState<string[]>([])
  const [localErrors, setLocalErrors] = useState<FieldErrors>({})
  // Corpo exato do último teste bem-sucedido; qualquer mudança trava o Salvar (llm-providers 34).
  const [testedDraft, setTestedDraft] = useState<string | null>(null)

  const parsed = toDraft(values, usesUrl)
  const current = "draft" in parsed ? JSON.stringify(parsed.draft) : null
  const canSave = current !== null && current === testedDraft
  const busy =
    test.isPending ||
    save.isPending ||
    activate.isPending ||
    remove.isPending ||
    listModels.isPending

  function clearFeedback() {
    test.reset()
    save.reset()
    activate.reset()
    remove.reset()
    listModels.reset()
    setLocalErrors({})
  }

  function update(name: keyof FormValues) {
    return (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setValues((prev) => ({ ...prev, [name]: event.target.value }))
      clearFeedback()
    }
  }

  function onTest() {
    clearFeedback()
    if ("fieldErrors" in parsed) {
      setLocalErrors(parsed.fieldErrors)
      return
    }
    const snapshot = JSON.stringify(parsed.draft)
    test.mutate(parsed.draft, {
      onSuccess: (result) => setTestedDraft(result.ok ? snapshot : null),
    })
  }

  // Corpo sem modelo: só chave (ou URL) importa para listar.
  function onLoadModels() {
    clearFeedback()
    if ("fieldErrors" in parsed) {
      setLocalErrors(parsed.fieldErrors)
      return
    }
    const { api_key, base_url } = parsed.draft
    listModels.mutate(
      { ...(api_key && { api_key }), ...(base_url && { base_url }) },
      {
        onSuccess: (result) => {
          if (!result.ok) return
          setModels(result.models)
          // Modelo padrão fora da lista da chave: cai no primeiro disponível.
          const first = result.models[0]
          if (first && !result.models.includes(values.model))
            setValues((prev) => ({ ...prev, model: first }))
        },
      }
    )
  }

  function onSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSave || !("draft" in parsed)) return
    clearFeedback()
    save.mutate(parsed.draft, {
      onSuccess: () => {
        setValues((prev) => ({ ...prev, api_key: "" }))
        setTestedDraft(null)
      },
    })
  }

  const fields = {
    ...errorFields(test.error),
    ...errorFields(save.error),
    ...localErrors,
  }
  const apiError =
    test.data && !test.data.ok
      ? test.data.message
      : listModels.data && !listModels.data.ok
        ? listModels.data.message
        : [
            test.error,
            save.error,
            activate.error,
            remove.error,
            listModels.error,
          ].find((error) => error && Object.keys(error.fields).length === 0)
            ?.message

  const keyHint =
    config.key_status === "unreadable"
      ? MESSAGES.keyUnreadable
      : configured && config.key_mask
        ? MESSAGES.keepKey(config.key_mask)
        : undefined

  return (
    <form
      id={formId}
      noValidate
      onSubmit={onSave}
      className="flex flex-col gap-4"
    >
      {usesUrl ? (
        <FormField
          label={MESSAGES.url}
          name="base_url"
          type="url"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          placeholder="http://host.docker.internal:11434"
          hint={OLLAMA_URL_HINT}
          error={fields.base_url}
          value={values.base_url}
          onChange={update("base_url")}
        />
      ) : (
        <FormField
          label={MESSAGES.apiKey}
          name="api_key"
          type="password"
          autoComplete="off"
          spellCheck={false}
          hint={keyHint}
          error={fields.api_key}
          value={values.api_key}
          onChange={update("api_key")}
        />
      )}
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_10rem]">
        <div className="flex flex-col gap-2">
          <ModelSelect
            label={MESSAGES.model}
            models={models}
            hint={models.length ? undefined : MESSAGES.modelsHint}
            error={fields.model}
            value={values.model}
            onChange={update("model")}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="self-start"
            onClick={onLoadModels}
            disabled={busy}
          >
            {listModels.isPending
              ? MESSAGES.loadingModels
              : MESSAGES.loadModels}
          </Button>
        </div>
        <FormField
          label={MESSAGES.contextWindow}
          name="context_window"
          type="number"
          inputMode="numeric"
          min={1}
          step={1}
          className="font-mono tabular-nums"
          hint={MESSAGES.contextWindowHint}
          error={fields.context_window}
          value={values.context_window}
          onChange={update("context_window")}
        />
      </div>

      <div aria-live="polite" className="text-sm empty:hidden">
        {listModels.data?.ok ? (
          <p className="motion-enter text-status-done">
            {MESSAGES.modelsLoaded(listModels.data.models.length)}
          </p>
        ) : test.data?.ok ? (
          <p className="motion-enter text-status-done">{MESSAGES.testOk}</p>
        ) : save.isSuccess ? (
          <p className="motion-enter text-status-done">{MESSAGES.saved}</p>
        ) : null}
      </div>
      <div role="alert" className="empty:hidden">
        {apiError ? (
          <p className="motion-enter rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {apiError}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onTest}
          disabled={busy}
        >
          {test.isPending ? MESSAGES.testing : MESSAGES.test}
        </Button>
        <Button
          type="submit"
          disabled={!canSave || busy}
          aria-describedby={canSave ? undefined : `${formId}-save-hint`}
        >
          {save.isPending ? MESSAGES.saving : MESSAGES.save}
        </Button>
        <span className="flex-1" />
        {config.state === "configured" ? (
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              clearFeedback()
              activate.mutate(undefined)
            }}
            disabled={busy}
          >
            {MESSAGES.activate}
          </Button>
        ) : null}
        {configured ? (
          <RemoveDialog
            providerLabel={label}
            disabled={busy}
            onConfirm={() => {
              clearFeedback()
              remove.mutate(undefined)
            }}
          />
        ) : null}
      </div>
      {canSave ? null : (
        <p id={`${formId}-save-hint`} className="text-sm text-muted-foreground">
          {MESSAGES.saveHint}
        </p>
      )}
    </form>
  )
}
