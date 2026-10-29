import { screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { bigBacklog } from "./fixtures/backlog-30-200"
import {
  backlog,
  meeting,
  record,
  renderReview,
  serve,
  story,
  TWO_EPICS,
} from "./testing"

it("agrupa as US por Epic com todos os campos (backlog-review 39)", async () => {
  serve(meeting())
  const { container } = renderReview()

  const cadastro = await screen.findByRole("region", { name: /Cadastro/ })
  const first = within(cadastro).getByRole("article", {
    name: "Cadastrar cliente",
  })
  for (const text of [
    "US-01",
    "atendente",
    "cadastrar cliente com CPF",
    "eu possa abrir pedidos",
    "CPF válido",
    "salvo",
    "o cliente aparece",
    "00:01:05",
  ])
    expect(within(first).getByText(text)).toBeInTheDocument()
  expect(within(first).getByLabelText("Prioridade")).toHaveValue("High")
  expect(within(first).getByLabelText("Story Points")).toHaveValue("5")
  expect(within(first).getByLabelText("Solicitante")).toHaveValue("1")
  const second = within(cadastro).getByRole("article", {
    name: "Buscar cliente",
  })
  expect(within(second).getByLabelText("Solicitante")).toHaveValue("")
  expect(screen.getByRole("region", { name: /Relatórios/ })).toBeInTheDocument()
  expect(await axe(container)).toHaveNoViolations()
})

it("texto da US com <script> sai escapado (SEC-12)", async () => {
  const evil = "<script>window.hacked = 1</script>"
  serve(
    meeting(),
    backlog([
      {
        id: 1,
        name: evil,
        user_stories: [
          story({ name: evil, as_a: "<img src=x onerror=alert(1)>" }),
        ],
      },
    ])
  )
  const { container } = renderReview()

  expect(await screen.findByRole("heading", { name: evil })).toBeInTheDocument()
  expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument()
  expect(container.querySelector("script")).toBeNull()
  expect(container.querySelector("img")).toBeNull()
})

it("em failed mostra só leitura, motivo e Tentar novamente com aviso (backlog-review 46)", async () => {
  serve(
    meeting({
      status: "failed",
      failed_stage: "generation",
      error_message: "O provedor recusou a chave.",
    }),
    backlog(TWO_EPICS, { read_only: true, last_generation_failed: true })
  )
  const retry = record("post", "/retry", () =>
    HttpResponse.json({}, { status: 202 })
  )
  const { container } = renderReview()

  // Notice warn tem role="status" (ADR-0024, "Componentes").
  const alert = (await screen.findByText(/A última geração falhou/)).closest(
    '[data-slot="notice"]'
  ) as HTMLElement
  expect(alert).toHaveAttribute("data-variant", "warn")
  expect(alert).toHaveAttribute("role", "status")
  expect(alert).toHaveTextContent("A última geração falhou")
  expect(alert).toHaveTextContent("O provedor recusou a chave.")
  expect(
    screen.queryByRole("button", { name: /^Editar/ })
  ).not.toBeInTheDocument()
  expect(
    screen.queryByRole("button", { name: "Regenerar" })
  ).not.toBeInTheDocument()
  expect(screen.queryByLabelText("Nova Epic")).not.toBeInTheDocument()

  await userEvent.click(
    within(alert).getByRole("button", { name: "Tentar novamente" })
  )
  const dialog = await screen.findByRole("alertdialog")
  expect(dialog).toHaveTextContent("todas as edições feitas nele se perdem")
  expect(await axe(container.ownerDocument.body)).toHaveNoViolations()
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Tentar novamente" })
  )
  expect(retry).toHaveLength(1)
})

it("erro do Tentar novamente aparece em Notice error (ADR-0024)", async () => {
  serve(
    meeting({ status: "failed", failed_stage: "generation" }),
    backlog(TWO_EPICS, { read_only: true, last_generation_failed: true })
  )
  record("post", "/retry", () =>
    HttpResponse.json(
      { error: { code: "conflict", message: "Já está em andamento." } },
      { status: 409 }
    )
  )
  const { container } = renderReview()

  await userEvent.click(
    await screen.findByRole("button", { name: "Tentar novamente" })
  )
  const dialog = await screen.findByRole("alertdialog")
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Tentar novamente" })
  )
  const alert = await screen.findByRole("alert")
  expect(alert).toHaveTextContent("Já está em andamento.")
  expect(alert).toHaveAttribute("data-variant", "error")
  expect(await axe(container)).toHaveNoViolations()
})

it.each([
  ["transcribed", "Transcrita"],
  ["generating", "Gerando backlog"],
  ["needs_split", "Precisa dividir"],
] as const)(
  "em %s com backlog mostra só leitura com o status (backlog-review 46)",
  async (status, label) => {
    serve(meeting({ status }), backlog(TWO_EPICS, { read_only: true }))
    renderReview()

    expect(
      await screen.findByText(
        new RegExp(`só para leitura. Situação atual: ${label}`)
      )
    ).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: /^Editar/ })
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: /^Excluir/ })
    ).not.toBeInTheDocument()
    expect(screen.getByText("Low")).toBeInTheDocument()
  }
)

it("sem backlog gravado avisa (backlog-review 4)", async () => {
  serve(meeting({ has_backlog: false }), { status: 409, code: "no_backlog" })
  renderReview()

  expect(
    await screen.findByText("Esta reunião ainda não tem backlog.")
  ).toBeInTheDocument()
})

it("backlog vazio em done convida a criar Epic (backlog-review 47)", async () => {
  serve(meeting(), backlog([]))
  renderReview()

  expect(
    await screen.findByText("Nenhuma User Story nesta geração.")
  ).toBeInTheDocument()
  expect(screen.getByLabelText("Nova Epic")).toBeInTheDocument()
})

it("recolhe e expande a Epic pelo teclado (ADR-0022)", async () => {
  serve(meeting())
  renderReview()

  const toggle = await screen.findByRole("button", {
    name: "Recolher Epic Cadastro",
  })
  expect(toggle).toHaveAttribute("aria-expanded", "true")
  toggle.focus()
  await userEvent.keyboard("{Enter}")
  expect(
    screen.getByRole("button", { name: "Expandir Epic Cadastro" })
  ).toHaveAttribute("aria-expanded", "false")
  expect(
    screen.queryByRole("article", { name: "Cadastrar cliente" })
  ).not.toBeInTheDocument()
})

it("Epic sem card, régua --ink no topo e título serif (ADR-0024)", async () => {
  serve(meeting())
  renderReview()

  const epic = await screen.findByRole("region", { name: /Cadastro/ })
  expect(epic).toHaveClass("border-t", "border-ink")
  expect(epic.className).not.toMatch(
    /\b(bg-|rounded|shadow|border-(x|b|l|r)\b)/
  )
  expect(within(epic).getByText("Cadastro")).toHaveClass("font-heading")
})

it("abrir e fechar a Epic anima só por classes de motion.css (ADR-0024)", async () => {
  serve(meeting())
  renderReview()

  const toggle = await screen.findByRole("button", {
    name: "Recolher Epic Cadastro",
  })
  expect(toggle.querySelector("svg")).toHaveClass("motion-rise")
  expect(toggle.querySelector("svg")).toHaveStyle({
    transform: "rotate(90deg)",
  })
  expect(
    document.getElementById(toggle.getAttribute("aria-controls")!)
  ).toHaveClass("motion-enter")
  await userEvent.click(toggle)
  expect(toggle.querySelector("svg")).toHaveStyle({ transform: "none" })
})

it("US como linha com régua, nome serif, US-id e instante em mono (ADR-0024)", async () => {
  serve(meeting())
  renderReview()

  const us = await screen.findByRole("article", { name: "Cadastrar cliente" })
  expect(us).toHaveClass("border-t", "border-hairline")
  expect(us.className).not.toMatch(/\b(bg-|rounded|shadow|p-\d)/)
  expect(
    within(us).getByRole("heading", { name: "Cadastrar cliente" })
  ).toHaveClass("font-heading")
  for (const text of ["US-01", "00:01:05"])
    expect(within(us).getByText(text)).toHaveClass("font-mono", "tabular-nums")
})

it("renderiza o backlog de fixture de 30 Epics e 200 US (NFR-04)", async () => {
  serve(meeting(), bigBacklog())
  renderReview()

  expect(await screen.findAllByRole("region")).toHaveLength(30)
  expect(screen.getAllByRole("article")).toHaveLength(200)
  expect(screen.getByText("30 Epics · 200 User Stories")).toBeInTheDocument()
}, 20_000)
