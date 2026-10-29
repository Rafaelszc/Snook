import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { server } from "@/test/server"

import {
  BASE,
  backlog,
  fieldError,
  meeting,
  record,
  renderReview,
  serve,
  TWO_EPICS,
} from "./testing"

function split(answer: "split" | "not_split") {
  server.use(
    http.get(`${BASE}/split`, () =>
      answer === "split"
        ? HttpResponse.json({ status: "done", read_only: true })
        : HttpResponse.json(
            { error: { code: "split_not_available", message: "x" } },
            { status: 409 }
          )
    )
  )
}

const regenerated = (status: string) => () =>
  HttpResponse.json({ status }, { status: 202 })

it("Regenerar avisa da perda das edições antes de confirmar (backlog-review 44)", async () => {
  serve(meeting())
  split("not_split")
  const calls = record("post", "/regenerate", regenerated("generating"))
  renderReview()

  await userEvent.click(
    await screen.findByRole("button", { name: "Regenerar" })
  )
  const dialog = await screen.findByRole("alertdialog", {
    name: "Regenerar o backlog?",
  })
  expect(dialog).toHaveTextContent("todas as edições feitas aqui se perdem")
  expect(calls).toEqual([])
  const confirm = await within(dialog).findByRole("button", {
    name: "Regenerar",
  })
  await waitFor(() => expect(confirm).toBeEnabled())
  expect(
    within(dialog).queryByRole("button", { name: "Reajustar cortes" })
  ).not.toBeInTheDocument()
  expect(await axe(document.body)).toHaveNoViolations()
  await userEvent.click(confirm)

  await waitFor(() => expect(calls).toEqual([{ mode: "same_cuts" }]))
})

it("Reunião dividida oferece mesmos cortes e reajustar (backlog-review 44)", async () => {
  serve(meeting())
  split("split")
  const calls = record("post", "/regenerate", regenerated("generating"))
  renderReview()

  await userEvent.click(
    await screen.findByRole("button", { name: "Regenerar" })
  )
  const dialog = await screen.findByRole("alertdialog")
  await userEvent.click(
    await within(dialog).findByRole("button", { name: "Mesmos cortes" })
  )

  await waitFor(() => expect(calls).toEqual([{ mode: "same_cuts" }]))
})

it("reajustar cortes leva à tela de divisão (backlog-review 27, 44)", async () => {
  serve(meeting())
  split("split")
  const calls = record("post", "/regenerate", regenerated("needs_split"))
  const { router } = renderReview()

  await userEvent.click(
    await screen.findByRole("button", { name: "Regenerar" })
  )
  await userEvent.click(
    await screen.findByRole("button", { name: "Reajustar cortes" })
  )

  await waitFor(() =>
    expect(router.state.location.pathname).toMatch(/\/split$/)
  )
  expect(calls).toEqual([{ mode: "adjust_cuts" }])
})

it("Exportar Markdown e JSON baixam o anexo da API (backlog-review 45)", async () => {
  serve(
    meeting({ status: "needs_split" }),
    backlog(TWO_EPICS, { read_only: true })
  )
  renderReview()

  const md = await screen.findByRole("link", { name: "Exportar Markdown" })
  const json = screen.getByRole("link", { name: "Exportar JSON" })
  expect(md).toHaveAttribute("href", `${BASE}/export?format=md`)
  expect(json).toHaveAttribute("href", `${BASE}/export?format=json`)
  expect(md).toHaveAttribute("download")
  expect(json).toHaveAttribute("download")
})

it.each(["transcribed", "needs_split"] as const)(
  "Renomear participante aparece com backlog só leitura em %s (backlog-review 48)",
  async (status) => {
    serve(meeting({ status }), backlog(TWO_EPICS, { read_only: true }))
    renderReview()

    expect(
      await screen.findByRole("button", { name: "Renomear participante" })
    ).toBeEnabled()
  }
)

it("em generating não oferece renomear nem regenerar (backlog-review, regras por status)", async () => {
  serve(
    meeting({ status: "generating" }),
    backlog(TWO_EPICS, { read_only: true })
  )
  renderReview()

  await screen.findByRole("link", { name: "Exportar JSON" })
  expect(
    screen.queryByRole("button", { name: "Renomear participante" })
  ).not.toBeInTheDocument()
  expect(
    screen.queryByRole("button", { name: "Regenerar" })
  ).not.toBeInTheDocument()
})

it("renomear participante com nome de outro avisa da união e mostra erro do campo (41)", async () => {
  serve(
    meeting({ status: "failed", failed_stage: "generation" }),
    backlog(TWO_EPICS, { read_only: true, last_generation_failed: true })
  )
  const calls = record(
    "patch",
    "/participants/1",
    fieldError("name", "Nome inválido.")
  )
  renderReview()

  await userEvent.click(
    await screen.findByRole("button", { name: "Renomear participante" })
  )
  const dialog = await screen.findByRole("dialog", {
    name: "Renomear participante",
  })
  const name = within(dialog).getByLabelText("Novo nome")
  expect(name).toHaveValue("Ana")
  await userEvent.clear(name)
  await userEvent.type(name, "bruno")
  expect(within(dialog).getByRole("status")).toHaveTextContent(
    'Já existe o participante "Bruno"'
  )
  expect(await axe(document.body)).toHaveNoViolations()
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Renomear" })
  )

  expect(await within(dialog).findByRole("alert")).toHaveTextContent(
    "Nome inválido."
  )
  expect(calls).toEqual([{ name: "bruno" }])
})

it("diálogo usa DialogSurface opaco, sem vidro (ADR-0024)", async () => {
  serve(meeting())
  split("not_split")
  renderReview()

  await userEvent.click(
    await screen.findByRole("button", { name: "Regenerar" })
  )
  await screen.findByRole("alertdialog")
  expect(
    document.querySelectorAll('[data-slot="dialog-surface"]')
  ).toHaveLength(1)
  expect(document.querySelector('[data-slot="glass-panel"]')).toBeNull()
})
