import { screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { partsFromCuts } from "./api"
import { renderSplit, serveRefresh, smallSplit, stubLayout } from "./testing"

stubLayout()

const confirmButton = () =>
  screen.getByRole("button", { name: "Confirmar divisão" })

function partRows() {
  return within(screen.getByRole("list", { name: "Partes" })).getAllByRole(
    "listitem"
  )
}

it("soma a estimativa por Parte e marca se cabe (34)", () => {
  const { segments } = smallSplit()
  expect(partsFromCuts(segments, [1], 250)).toMatchObject([
    {
      index: 1,
      first: 0,
      last: 1,
      startSeconds: 0,
      endSeconds: 115,
      tokens: 200,
      fits: true,
    },
    {
      index: 2,
      first: 2,
      last: 3,
      startSeconds: 120,
      endSeconds: 235,
      tokens: 200,
      fits: true,
    },
  ])
  expect(partsFromCuts(segments, [], 250)[0]).toMatchObject({
    tokens: 400,
    fits: false,
  })
  // Orçamento zero ou negativo: nada cabe (RT-10).
  expect(partsFromCuts(segments, [0, 1, 2], 0).every((p) => !p.fits)).toBe(true)
})

it("mostra intervalo, estimativa e se cabe por Parte (34)", async () => {
  serveRefresh(smallSplit())
  const { container } = renderSplit()

  await screen.findByRole("list", { name: "Partes" })
  const rows = partRows()
  expect(rows).toHaveLength(2)
  expect(within(rows[0]).getByText("00:00:00 a 00:01:55")).toBeVisible()
  expect(within(rows[0]).getByText("200 tokens")).toBeVisible()
  expect(within(rows[0]).getByText("Cabe")).toBeVisible()
  expect(within(rows[1]).getByText("00:02:00 a 00:03:55")).toBeVisible()
  expect(confirmButton()).toBeEnabled()
  expect(await axe(container)).toHaveNoViolations()
})

it("remover um corte junta as Partes e desabilita confirmar (33, 35)", async () => {
  serveRefresh(smallSplit({ cuts: [2] }))
  const user = userEvent.setup()
  renderSplit()

  await user.click(
    await screen.findByRole("button", { name: /Fim da parte 1/ })
  )
  const rows = partRows()
  expect(rows).toHaveLength(1)
  expect(within(rows[0]).getByText("400 tokens")).toBeVisible()
  expect(within(rows[0]).getByText("Não cabe")).toBeVisible()
  expect(confirmButton()).toBeDisabled()
  expect(screen.getByText(/1 parte, 1 não cabe/)).toBeVisible()
})

it("adiciona corte no fim de qualquer segmento, por teclado (33)", async () => {
  serveRefresh(smallSplit({ cuts: [2] }))
  const user = userEvent.setup()
  renderSplit()

  const add = await screen.findByRole("button", {
    name: "Cortar aqui depois da fala de 00:02:55",
  })
  add.focus()
  await user.keyboard("{Enter}")
  expect(
    screen.getByRole("button", {
      name: /Fim da parte 2 depois da fala de 00:02:55/,
    })
  ).toHaveAttribute("aria-pressed", "true")
  expect(partRows()).toHaveLength(3)
})

it("move o corte com as setas e o foco acompanha (33)", async () => {
  serveRefresh(smallSplit({ cuts: [2] }))
  const user = userEvent.setup()
  renderSplit()

  const cut = await screen.findByRole("button", { name: /Fim da parte 1/ })
  expect(cut).toHaveAccessibleName("Fim da parte 1 depois da fala de 00:01:55")
  cut.focus()
  await user.keyboard("{ArrowUp}")

  const moved = screen.getByRole("button", { name: /Fim da parte 1/ })
  expect(moved).toHaveAccessibleName(
    "Fim da parte 1 depois da fala de 00:00:55"
  )
  expect(moved).toHaveFocus()
  expect(within(partRows()[0]).getByText("100 tokens")).toBeVisible()
  expect(within(partRows()[1]).getByText("300 tokens")).toBeVisible()
  expect(confirmButton()).toBeDisabled()

  // Primeira fala: não há fim de segmento acima.
  await user.keyboard("{ArrowUp}")
  expect(
    screen.getByRole("button", { name: /Fim da parte 1/ })
  ).toHaveAccessibleName("Fim da parte 1 depois da fala de 00:00:55")

  await user.keyboard("{ArrowDown}{ArrowDown}")
  expect(
    screen.getByRole("button", { name: /Fim da parte 1/ })
  ).toHaveAccessibleName("Fim da parte 1 depois da fala de 00:02:55")
  expect(confirmButton()).toBeDisabled()
})

it("não move para cima de outro corte", async () => {
  serveRefresh(smallSplit({ cuts: [1, 2] }))
  const user = userEvent.setup()
  renderSplit()

  const second = await screen.findByRole("button", { name: /Fim da parte 2/ })
  second.focus()
  await user.keyboard("{ArrowUp}")
  expect(
    screen.getByRole("button", { name: /Fim da parte 2/ })
  ).toHaveAccessibleName("Fim da parte 2 depois da fala de 00:01:55")
  expect(partRows()).toHaveLength(3)
})

it("não oferece corte no meio de um segmento (33)", async () => {
  serveRefresh(smallSplit())
  renderSplit()

  const region = await screen.findByRole("region", {
    name: "Segmentos da reunião",
  })
  // Uma fronteira por segmento, menos o último: 3 botões para 4 falas.
  expect(within(region).getAllByRole("button")).toHaveLength(3)
})

it("Ata: Parte que cabe em --done; corte ativo em --signal com transform", async () => {
  serveRefresh(smallSplit())
  renderSplit()

  await screen.findByRole("list", { name: "Partes" })
  expect(within(partRows()[0]).getByText("Cabe")).toHaveClass("text-done")
  const active = screen.getAllByRole("button", { pressed: true })[0]
  expect(active).toHaveClass("bg-signal", "motion-press")
})
