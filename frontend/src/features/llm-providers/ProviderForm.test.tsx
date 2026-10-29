import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

import type { LlmConfig } from "./api"
import { CONFIGURED, NOT_CONFIGURED } from "./fixtures"
import { SettingsPage } from "./SettingsPage"

const REJECTED = "O provedor recusou a chave."

function listReturns(configs: LlmConfig[]) {
  server.use(http.get("/api/llm-configs", () => HttpResponse.json(configs)))
}

function testReturns(result: object, onBody?: (body: unknown) => void) {
  server.use(
    http.post("/api/llm-configs/:provider/test", async ({ request }) => {
      onBody?.(await request.json())
      return HttpResponse.json(result)
    })
  )
}

async function openSection(name: string) {
  return screen.findByRole("region", { name })
}

it("Salvar fica desabilitado até um teste bem-sucedido com os valores atuais (llm-providers 34)", async () => {
  const user = userEvent.setup()
  let sent: unknown
  listReturns(NOT_CONFIGURED)
  testReturns({ ok: true }, (body) => (sent = body))
  renderWithProviders(<SettingsPage />)

  const openai = within(await openSection("OpenAI"))
  const save = openai.getByRole("button", { name: "Salvar" })
  expect(save).toBeDisabled()

  await user.type(openai.getByLabelText("Chave de API"), "TesteChave-123456789")
  await user.click(openai.getByRole("button", { name: "Testar conexão" }))
  expect(await openai.findByText("Conexão bem-sucedida.")).toBeVisible()
  expect(save).toBeEnabled()
  expect(sent).toEqual({
    api_key: "TesteChave-123456789",
    model: "gpt-5-mini",
    context_window: 400000,
  })

  // Mudar qualquer campo invalida o teste anterior.
  await user.type(openai.getByLabelText("Chave de API"), "x")
  expect(save).toBeDisabled()
})

it("Carregar modelos preenche o select com os modelos da chave", async () => {
  const user = userEvent.setup()
  let sent: unknown
  listReturns(NOT_CONFIGURED)
  server.use(
    http.post("/api/llm-configs/deepseek/models", async ({ request }) => {
      sent = await request.json()
      return HttpResponse.json({
        ok: true,
        models: ["deepseek-chat", "deepseek-reasoner"],
      })
    })
  )
  renderWithProviders(<SettingsPage />)

  const deepseek = within(await openSection("DeepSeek"))
  await user.type(
    deepseek.getByLabelText("Chave de API"),
    "TesteChave-123456789"
  )
  await user.click(deepseek.getByRole("button", { name: "Carregar modelos" }))
  expect(await deepseek.findByText("2 modelos disponíveis.")).toBeVisible()
  expect(sent).toEqual({ api_key: "TesteChave-123456789" })

  await user.selectOptions(
    deepseek.getByLabelText("Modelo"),
    "deepseek-reasoner"
  )
  expect(deepseek.getByLabelText("Modelo")).toHaveValue("deepseek-reasoner")
})

it("teste que falha mostra o motivo da API e mantém Salvar desabilitado (llm-providers 35)", async () => {
  const user = userEvent.setup()
  listReturns(NOT_CONFIGURED)
  testReturns({ ok: false, reason: "credential_rejected", message: REJECTED })
  renderWithProviders(<SettingsPage />)

  const openai = within(await openSection("OpenAI"))
  await user.type(openai.getByLabelText("Chave de API"), "sk-errada-123456")
  await user.click(openai.getByRole("button", { name: "Testar conexão" }))
  const alert = await openai.findByRole("alert")
  expect(alert).toHaveTextContent(REJECTED)
  expect(alert).toHaveAttribute("data-variant", "error")
  expect(openai.getByRole("button", { name: "Salvar" })).toBeDisabled()
})

it("Salvar é o botão accent; campos com foco opaco (ADR-0024)", async () => {
  listReturns(NOT_CONFIGURED)
  renderWithProviders(<SettingsPage />)

  const openai = within(await openSection("OpenAI"))
  expect(openai.getByRole("button", { name: "Salvar" })).toHaveAttribute(
    "data-variant",
    "accent"
  )
  expect(
    openai.getByRole("button", { name: "Testar conexão" })
  ).toHaveAttribute("data-variant", "secondary")
  const model = openai.getByLabelText("Modelo")
  expect(model).toHaveClass("focus-visible:ring-2", "focus-visible:ring-ring")
  expect(model.className).not.toMatch(/ring-ring\/|ring-3/)
})

it("erro 422 do teste aparece no campo (llm-providers 35, 38)", async () => {
  const user = userEvent.setup()
  listReturns(NOT_CONFIGURED)
  server.use(
    http.post("/api/llm-configs/ollama/test", () =>
      HttpResponse.json(
        {
          error: {
            code: "invalid_url_scheme",
            message: "Use uma URL http ou https.",
            fields: { base_url: "Use uma URL http ou https." },
          },
        },
        { status: 422 }
      )
    )
  )
  renderWithProviders(<SettingsPage />)

  const ollama = within(await openSection("Ollama"))
  await user.type(ollama.getByLabelText("URL"), "ftp://x")
  await user.click(ollama.getByRole("button", { name: "Testar conexão" }))
  await waitFor(() =>
    expect(ollama.getByLabelText("URL")).toHaveAccessibleDescription(
      "Use uma URL http ou https."
    )
  )
  expect(ollama.getByLabelText("URL")).toHaveAttribute("aria-invalid", "true")
})

it("salva com os valores testados e mostra erro de gravação (llm-providers 35)", async () => {
  const user = userEvent.setup()
  let saved: unknown
  listReturns(CONFIGURED)
  testReturns({ ok: true })
  server.use(
    http.put("/api/llm-configs/anthropic", async ({ request }) => {
      saved = await request.json()
      return HttpResponse.json(
        {
          error: {
            code: "provider_unreachable",
            message: "Provedor inacessível.",
          },
        },
        { status: 422 }
      )
    })
  )
  renderWithProviders(<SettingsPage />)

  const anthropic = within(await openSection("Anthropic"))
  await user.click(anthropic.getByRole("button", { name: "Testar conexão" }))
  await user.click(await anthropic.findByRole("button", { name: "Salvar" }))
  expect(await anthropic.findByRole("alert")).toHaveTextContent(
    "Provedor inacessível."
  )
  // Chave vazia na edição mantém a atual: não vai no corpo (llm-providers 36).
  expect(saved).toEqual({ model: "claude-sonnet-4-5", context_window: 200000 })
})

it("salvar com sucesso limpa a chave e atualiza a lista", async () => {
  const user = userEvent.setup()
  let configs = NOT_CONFIGURED
  server.use(http.get("/api/llm-configs", () => HttpResponse.json(configs)))
  testReturns({ ok: true })
  server.use(
    http.put("/api/llm-configs/openai", () => {
      configs = [
        { ...CONFIGURED[0], model: "gpt-5-mini", context_window: 400000 },
        ...NOT_CONFIGURED.slice(1),
      ]
      return HttpResponse.json(configs[0])
    })
  )
  renderWithProviders(<SettingsPage />)

  const openai = within(await openSection("OpenAI"))
  await user.type(openai.getByLabelText("Chave de API"), "TesteChave-123456789")
  await user.click(openai.getByRole("button", { name: "Testar conexão" }))
  await user.click(await openai.findByRole("button", { name: "Salvar" }))
  expect(await openai.findByText("sk-...abcd")).toBeVisible()
  expect(openai.getByLabelText("Chave de API")).toHaveValue("")
  expect(openai.getByText("Ativo")).toBeVisible()
})

it("torna ativo um provedor configurado (llm-providers 19)", async () => {
  const user = userEvent.setup()
  let activated = ""
  listReturns(CONFIGURED)
  server.use(
    http.post("/api/llm-configs/:provider/activate", ({ params }) => {
      activated = String(params.provider)
      return HttpResponse.json({ ...CONFIGURED[1], state: "active" })
    })
  )
  renderWithProviders(<SettingsPage />)

  const anthropic = within(await openSection("Anthropic"))
  await user.click(anthropic.getByRole("button", { name: "Tornar ativo" }))
  await waitFor(() => expect(activated).toBe("anthropic"))
  expect(
    within(screen.getByRole("region", { name: "OpenAI" })).queryByRole(
      "button",
      { name: "Tornar ativo" }
    )
  ).toBeNull()
})

it("remover pede confirmação antes de chamar a API (llm-providers 37)", async () => {
  const user = userEvent.setup()
  let deleted = 0
  listReturns(CONFIGURED)
  server.use(
    http.delete("/api/llm-configs/anthropic", () => {
      deleted += 1
      return new HttpResponse(null, { status: 204 })
    })
  )
  renderWithProviders(<SettingsPage />)

  const anthropic = within(await openSection("Anthropic"))
  await user.click(anthropic.getByRole("button", { name: "Remover" }))
  const dialog = await screen.findByRole("alertdialog", {
    name: "Remover Anthropic?",
  })
  expect(dialog).toHaveAttribute("data-slot", "dialog-surface")
  expect(deleted).toBe(0)

  await user.click(within(dialog).getByRole("button", { name: "Cancelar" }))
  expect(screen.queryByRole("alertdialog")).toBeNull()
  expect(deleted).toBe(0)

  await user.click(anthropic.getByRole("button", { name: "Remover" }))
  await user.click(
    within(await screen.findByRole("alertdialog")).getByRole("button", {
      name: "Remover configuração",
    })
  )
  await waitFor(() => expect(deleted).toBe(1))
})

it("provedor não configurado não oferece remover nem ativar", async () => {
  listReturns(NOT_CONFIGURED)
  renderWithProviders(<SettingsPage />)

  const deepseek = within(await openSection("DeepSeek"))
  expect(deepseek.queryByRole("button", { name: "Remover" })).toBeNull()
  expect(deepseek.queryByRole("button", { name: "Tornar ativo" })).toBeNull()
})

it("feedback do teste entra com classe de movimento que respeita reduced-motion", async () => {
  const user = userEvent.setup()
  listReturns(NOT_CONFIGURED)
  testReturns({ ok: true })
  renderWithProviders(<SettingsPage />)

  const openai = within(await openSection("OpenAI"))
  await user.type(openai.getByLabelText("Chave de API"), "TesteChave-123456789")
  await user.click(openai.getByRole("button", { name: "Testar conexão" }))
  expect(await openai.findByText("Conexão bem-sucedida.")).toHaveClass(
    "motion-enter"
  )
})

it("diálogo de remover passa no axe", async () => {
  const user = userEvent.setup()
  listReturns(CONFIGURED)
  renderWithProviders(<SettingsPage />)

  const anthropic = within(await openSection("Anthropic"))
  await user.click(anthropic.getByRole("button", { name: "Remover" }))
  await screen.findByRole("alertdialog")
  expect(await axe(document.body)).toHaveNoViolations()
})
