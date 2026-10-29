import { screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { server } from "@/test/server"

import { split2h, SPLIT_2H_COUNT } from "./fixtures/split-2h"
import {
  ID,
  renderSplit,
  serveRefresh,
  smallSplit,
  stubLayout,
} from "./testing"

stubLayout()

it("ao abrir chama o refresh e explica a divisão (31, 47)", async () => {
  const calls = serveRefresh(smallSplit())
  const { container, router } = renderSplit()

  expect(await screen.findByText(/cerca de 400 tokens.*até 250/)).toBeVisible()
  expect(
    screen.getByText(/Provedor ativo: Anthropic, modelo claude-haiku-4-5\./)
  ).toBeVisible()
  expect(calls()).toBe(1)
  expect(await axe(container)).toHaveNoViolations()

  await userEvent.click(
    screen.getByRole("link", { name: "Trocar de modelo nas configurações" })
  )
  expect(router.state.location.pathname).toBe("/settings")
})

it("refresh que passou a caber leva ao detalhe sem mostrar cortes (47)", async () => {
  serveRefresh({
    ...smallSplit(),
    status: "generating",
    segments: [],
    cuts: [],
  })
  const { router } = renderSplit()

  expect(await screen.findByText("detalhe")).toBeVisible()
  expect(router.state.location.pathname).toBe(`/meetings/${ID}`)
  expect(
    screen.queryByRole("region", { name: "Segmentos da reunião" })
  ).not.toBeInTheDocument()
})

it("mostra segmentos em ordem com instante, nome e cortes sugeridos (32)", async () => {
  serveRefresh(smallSplit())
  renderSplit()

  const region = await screen.findByRole("region", {
    name: "Segmentos da reunião",
  })
  const rows = within(region).getAllByRole("listitem")
  expect(rows).toHaveLength(4)
  expect(within(rows[0]).getByText("00:00:00")).toBeVisible()
  expect(within(rows[0]).getByText("Ana")).toBeVisible()
  expect(within(rows[1]).getByText("00:01:00")).toBeVisible()
  expect(within(rows[1]).getByText("Bruno")).toBeVisible()
  expect(
    within(rows[1]).getByRole("button", { name: /Fim da parte 1/ })
  ).toHaveAttribute("aria-pressed", "true")
  expect(
    within(rows[0]).getByRole("button", { name: /Cortar aqui/ })
  ).toHaveAttribute("aria-pressed", "false")
  // Última fala: fim da reunião, sem corte.
  expect(within(rows[3]).queryByRole("button")).not.toBeInTheDocument()
})

it("2 h de fixture: só os segmentos perto da área visível no DOM (NFR-07)", async () => {
  serveRefresh(split2h())
  renderSplit()

  const region = await screen.findByRole("region", {
    name: "Segmentos da reunião",
  })
  const rendered = within(region).getAllByRole("listitem").length
  expect(rendered).toBeGreaterThan(0)
  expect(rendered).toBeLessThan(SPLIT_2H_COUNT / 10)
  const parts = screen.getByRole("list", { name: "Partes" })
  expect(within(parts).getAllByRole("listitem")).toHaveLength(3)
})

it("confirma os cortes e leva ao detalhe (12, 36)", async () => {
  let body: unknown
  server.use(
    http.put(`/api/meetings/${ID}/split`, async ({ request }) => {
      body = await request.json()
      return HttpResponse.json({ status: "generating" }, { status: 202 })
    })
  )
  const calls = serveRefresh(smallSplit())
  const { router } = renderSplit()

  await userEvent.click(
    await screen.findByRole("button", { name: "Confirmar divisão" })
  )
  expect(await screen.findByText("detalhe")).toBeVisible()
  expect(router.state.location.pathname).toBe(`/meetings/${ID}`)
  expect(body).toEqual({ cuts: [2] })
  // Confirmar não refaz o `refresh`.
  expect(calls()).toBe(1)
})

it("mostra a recusa da API e fica na tela (15)", async () => {
  serveRefresh(smallSplit())
  server.use(
    http.put(`/api/meetings/${ID}/split`, () =>
      HttpResponse.json(
        {
          error: {
            code: "part_too_large",
            message: "A parte 1 não cabe no modelo.",
            fields: {},
          },
        },
        { status: 422 }
      )
    )
  )
  const { router } = renderSplit()

  await userEvent.click(
    await screen.findByRole("button", { name: "Confirmar divisão" })
  )
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "A parte 1 não cabe no modelo."
  )
  expect(router.state.location.pathname).toBe(`/meetings/${ID}/split`)
})

it("fora de needs_split, avisa que não há divisão (11)", async () => {
  serveRefresh({ status: 409, code: "split_not_available" })
  renderSplit()

  expect(
    await screen.findByText("Esta reunião não está esperando divisão.")
  ).toBeVisible()
})

it("reunião de outro usuário ou inexistente: não encontrada (28)", async () => {
  serveRefresh({ status: 404, code: "meeting_not_found" })
  renderSplit()

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Reunião não encontrada."
  )
})

it("Ata: confirmar é o único accent; fala em serif, instante em mono", async () => {
  serveRefresh(smallSplit({ can_cancel: true }))
  const { container } = renderSplit()

  const confirm = await screen.findByRole("button", {
    name: "Confirmar divisão",
  })
  expect(confirm).toHaveAttribute("data-variant", "accent")
  expect(container.querySelectorAll('[data-variant="accent"]')).toHaveLength(1)
  expect(
    container.querySelector('[data-slot="page-header"] h1')
  ).toHaveTextContent("Dividir reunião")

  const region = screen.getByRole("region", { name: "Segmentos da reunião" })
  const first = within(region).getAllByRole("listitem")[0]
  expect(first.querySelector("p")).toHaveClass("font-serif")
  expect(within(first).getByText("00:00:00")).toHaveClass(
    "font-mono",
    "tabular-nums"
  )
})

it("Ata: recusa da API vira Notice de erro", async () => {
  serveRefresh(smallSplit())
  server.use(
    http.put(`/api/meetings/${ID}/split`, () =>
      HttpResponse.json(
        { error: { code: "x", message: "Recusado." } },
        { status: 409 }
      )
    )
  )
  renderSplit()

  await userEvent.click(
    await screen.findByRole("button", { name: "Confirmar divisão" })
  )
  const alert = await screen.findByRole("alert")
  expect(alert).toHaveTextContent("Recusado.")
  expect(alert).toHaveAttribute("data-slot", "notice")
  expect(alert).toHaveAttribute("data-variant", "error")
})
