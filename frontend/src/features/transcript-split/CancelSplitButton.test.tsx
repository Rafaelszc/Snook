import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { server } from "@/test/server"

import {
  ID,
  renderSplit,
  serveRefresh,
  smallSplit,
  stubLayout,
} from "./testing"

stubLayout()

const cancelButton = () =>
  screen.queryByRole("button", { name: "Cancelar divisão" })

it("com backlog gravado, cancela e volta à revisão do backlog (45)", async () => {
  serveRefresh(smallSplit({ can_cancel: true, split_reason: "adjust" }))
  let canceled = false
  server.use(
    http.post(`/api/meetings/${ID}/split/cancel`, () => {
      canceled = true
      return HttpResponse.json({ status: "done" })
    })
  )
  const { container, router } = renderSplit()

  expect(
    await screen.findByText("Reajuste os cortes antes de regenerar o backlog.")
  ).toBeVisible()
  expect(await axe(container)).toHaveNoViolations()
  await userEvent.click(cancelButton()!)
  expect(await screen.findByText("revisão")).toBeVisible()
  expect(router.state.location.pathname).toBe(`/meetings/${ID}/backlog`)
  expect(canceled).toBe(true)
})

it("sem backlog gravado, não mostra o botão (45)", async () => {
  serveRefresh(smallSplit({ can_cancel: false }))
  renderSplit()

  await screen.findByRole("button", { name: "Confirmar divisão" })
  expect(cancelButton()).not.toBeInTheDocument()
})

it("mostra a recusa do cancelamento e fica na tela", async () => {
  serveRefresh(smallSplit({ can_cancel: true }))
  server.use(
    http.post(`/api/meetings/${ID}/split/cancel`, () =>
      HttpResponse.json(
        {
          error: {
            code: "split_cancel_not_allowed",
            message: "Esta reunião não tem backlog para manter.",
          },
        },
        { status: 409 }
      )
    )
  )
  const { router } = renderSplit()

  await userEvent.click(
    await screen.findByRole("button", { name: "Cancelar divisão" })
  )
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Esta reunião não tem backlog para manter."
  )
  expect(router.state.location.pathname).toBe(`/meetings/${ID}/split`)
})

it("sem provedor ativo, mostra só a mensagem com link para configurações (44)", async () => {
  serveRefresh(
    smallSplit({
      message: "Nenhum provedor de LLM ativo. Ative um nas configurações.",
      can_cancel: true,
      provider: null,
      model: null,
      budget: null,
      total_tokens: null,
      segments: [],
      cuts: [],
    })
  )
  const { container, router } = renderSplit()

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Nenhum provedor de LLM ativo."
  )
  expect(screen.queryByRole("region")).not.toBeInTheDocument()
  expect(
    screen.queryByRole("button", { name: "Confirmar divisão" })
  ).not.toBeInTheDocument()
  expect(cancelButton()).not.toBeInTheDocument()
  expect(await axe(container)).toHaveNoViolations()

  await userEvent.click(
    screen.getByRole("link", { name: "Abrir configurações" })
  )
  expect(router.state.location.pathname).toBe("/settings")
})
