import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

import type { LlmConfig } from "./api"
import { CONFIGURED, NOT_CONFIGURED } from "./fixtures"
import { SettingsPage } from "./SettingsPage"

function listReturns(configs: LlmConfig[]) {
  server.use(http.get("/api/llm-configs", () => HttpResponse.json(configs)))
}

function section(name: string) {
  return screen.getByRole("region", { name })
}

it("mostra os 4 provedores com estado, máscara, modelo, janela e ativo (llm-providers 33)", async () => {
  listReturns(CONFIGURED)
  renderWithProviders(<SettingsPage />)

  const openai = await screen.findByRole("region", { name: "OpenAI" })
  expect(within(openai).getByText("Ativo")).toBeVisible()
  expect(within(openai).getByText("sk-...abcd")).toBeVisible()
  expect(within(openai).getByLabelText("Modelo")).toHaveValue("gpt-5")
  expect(within(openai).getByText("300.000 tokens")).toBeVisible()

  const anthropic = section("Anthropic")
  expect(within(anthropic).getByText("Configurado")).toBeVisible()
  expect(within(anthropic).getByText("...")).toBeVisible()

  expect(within(section("DeepSeek")).getByText("Não configurado")).toBeVisible()

  const ollama = section("Ollama")
  expect(
    within(ollama).getByText("http://host.docker.internal:11434")
  ).toBeVisible()
  expect(within(ollama).queryByLabelText("Chave de API")).toBeNull()
})

it("sem configuração, sugere modelo e janela padrão (llm-providers 1)", async () => {
  listReturns(NOT_CONFIGURED)
  renderWithProviders(<SettingsPage />)

  const deepseek = await screen.findByRole("region", { name: "DeepSeek" })
  expect(within(deepseek).getByLabelText("Modelo")).toHaveValue("deepseek-chat")
  expect(within(deepseek).getByLabelText("Janela de contexto")).toHaveValue(
    128000
  )
})

it("campo de chave nunca vem preenchido e mostra a máscara como referência (llm-providers 36)", async () => {
  listReturns(CONFIGURED)
  renderWithProviders(<SettingsPage />)

  const openai = await screen.findByRole("region", { name: "OpenAI" })
  const key = within(openai).getByLabelText("Chave de API")
  expect(key).toHaveValue("")
  expect(key).toHaveAttribute("type", "password")
  expect(key).toHaveAccessibleDescription(
    "Deixe vazio para manter a chave atual (sk-...abcd)."
  )
})

it("chave ilegível pede nova chave (ADR-0009)", async () => {
  listReturns([
    { ...CONFIGURED[0], key_status: "unreadable", key_mask: null },
    ...CONFIGURED.slice(1),
  ])
  renderWithProviders(<SettingsPage />)

  const openai = await screen.findByRole("region", { name: "OpenAI" })
  expect(
    within(openai).getByText("Chave ilegível. Digite a chave de novo.")
  ).toBeVisible()
})

it("mostra erro da API ao listar", async () => {
  server.use(
    http.get("/api/llm-configs", () =>
      HttpResponse.json(
        { error: { code: "internal_error", message: "erro interno" } },
        { status: 500 }
      )
    )
  )
  renderWithProviders(<SettingsPage />)
  const alert = await screen.findByRole("alert")
  expect(alert).toHaveTextContent("erro interno")
  expect(alert).toHaveAttribute("data-variant", "error")
})

it("provedores em linhas com régua, sem card; ativo em --done (ADR-0024)", async () => {
  listReturns(CONFIGURED)
  renderWithProviders(<SettingsPage />)

  const openai = await screen.findByRole("region", { name: "OpenAI" })
  for (const name of ["OpenAI", "Anthropic", "DeepSeek", "Ollama"])
    expect(section(name).className).not.toMatch(
      /\b(bg-|rounded|shadow|border\b)/
    )
  expect(openai.parentElement).toHaveClass("divide-hairline", "border-t-ink")
  expect(within(openai).getByText("Ativo")).toHaveClass("text-done")
  expect(within(openai).getByRole("heading", { name: "OpenAI" })).toHaveClass(
    "font-heading"
  )
})

it("passa no axe sem erro", async () => {
  listReturns(CONFIGURED)
  const { container } = renderWithProviders(<SettingsPage />)
  await screen.findByRole("region", { name: "OpenAI" })
  expect(await axe(container)).toHaveNoViolations()
})
