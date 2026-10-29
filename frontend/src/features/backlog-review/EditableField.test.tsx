import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { fieldError, meeting, record, renderReview, serve } from "./testing"

async function firstStory() {
  serve(meeting())
  const view = renderReview()
  const card = await screen.findByRole("article", { name: "Cadastrar cliente" })
  return { ...view, card }
}

it("edita o nome da US no lugar e salva com Enter (backlog-review 40)", async () => {
  const calls = record("patch", "/user-stories/11")
  const { card } = await firstStory()

  await userEvent.click(
    within(card).getByRole("button", { name: "Editar Nome da User Story" })
  )
  const input = within(card).getByRole("textbox", {
    name: "Nome da User Story",
  })
  expect(input).toHaveFocus()
  await userEvent.clear(input)
  await userEvent.type(input, "Cadastrar cliente PJ{Enter}")

  await waitFor(() => expect(calls).toEqual([{ name: "Cadastrar cliente PJ" }]))
})

it("Esc cancela sem chamar a API e devolve o foco", async () => {
  const calls = record("patch", "/user-stories/11")
  const { card } = await firstStory()

  const edit = within(card).getByRole("button", { name: "Editar Como" })
  await userEvent.click(edit)
  await userEvent.type(
    within(card).getByRole("textbox", { name: "Como" }),
    " sênior{Escape}"
  )

  expect(calls).toEqual([])
  await waitFor(() =>
    expect(
      within(card).getByRole("button", { name: "Editar Como" })
    ).toHaveFocus()
  )
})

it("texto longo salva pelo botão e erro 422 aparece junto ao campo (backlog-review 40)", async () => {
  record(
    "patch",
    "/user-stories/11",
    fieldError("so_that", "No máximo 2000 caracteres.")
  )
  const { card, container } = await firstStory()

  await userEvent.click(
    within(card).getByRole("button", { name: "Editar Para" })
  )
  const area = within(card).getByRole("textbox", { name: "Para" })
  await userEvent.type(area, " hoje")
  await userEvent.click(within(card).getByRole("button", { name: "Salvar" }))

  const error = await within(card).findByRole("alert")
  expect(error).toHaveTextContent("No máximo 2000 caracteres.")
  expect(area).toHaveAttribute("aria-invalid", "true")
  expect(area).toHaveAccessibleDescription("No máximo 2000 caracteres.")
  expect(await axe(container)).toHaveNoViolations()
})

it("prioridade, story points e solicitante salvam na troca (backlog-review 40)", async () => {
  const calls = record("patch", "/user-stories/11")
  const { card } = await firstStory()

  await userEvent.selectOptions(
    within(card).getByLabelText("Prioridade"),
    "Low"
  )
  await userEvent.selectOptions(
    within(card).getByLabelText("Story Points"),
    "13"
  )
  await userEvent.selectOptions(within(card).getByLabelText("Solicitante"), "")

  await waitFor(() =>
    expect(calls).toEqual([
      { priority: "Low" },
      { story_points: 13 },
      { requested_by: null },
    ])
  )
})

it("instante vazio vai como null e erro de duração aparece no campo (backlog-review 40)", async () => {
  const calls = record(
    "patch",
    "/user-stories/11",
    fieldError("requested_at", "O instante passa da duração da gravação.")
  )
  const { card } = await firstStory()

  await userEvent.click(
    within(card).getByRole("button", { name: "Editar Quando" })
  )
  const input = within(card).getByRole("textbox", { name: "Quando" })
  await userEvent.clear(input)
  await userEvent.type(input, "09:00:00{Enter}")

  expect(
    await within(card).findByText("O instante passa da duração da gravação.")
  ).toBeInTheDocument()
  await userEvent.clear(input)
  await userEvent.type(input, "{Enter}")
  await waitFor(() =>
    expect(calls).toEqual([
      { requested_at: "09:00:00" },
      { requested_at: null },
    ])
  )
})

it("edita critério de aceite (backlog-review 40)", async () => {
  const calls = record("patch", "/criteria/101")
  const { card } = await firstStory()

  await userEvent.click(
    within(card).getByRole("button", { name: "Editar Então do critério" })
  )
  const area = within(card).getByRole("textbox", { name: "Então do critério" })
  await userEvent.clear(area)
  await userEvent.type(
    area,
    "o cliente aparece na lista{Control>}{Enter}{/Control}"
  )

  await waitFor(() =>
    expect(calls).toEqual([{ then: "o cliente aparece na lista" }])
  )
})

it("nome da Epic editável com Tab e Enter (backlog-review 40)", async () => {
  const calls = record("patch", "/epics/1")
  await firstStory()

  const edit = screen.getByRole("button", {
    name: "Editar Nome da Epic Cadastro",
  })
  edit.focus()
  await userEvent.keyboard("{Enter}")
  const input = screen.getByRole("textbox", { name: "Nome da Epic Cadastro" })
  await userEvent.type(input, " de clientes{Enter}")

  await waitFor(() => expect(calls).toEqual([{ name: "Cadastro de clientes" }]))
})

it("campos com 40 px e anel de foco opaco de 2 px (ADR-0024, Foco)", async () => {
  const { card, container } = await firstStory()

  await userEvent.click(
    within(card).getByRole("button", { name: "Editar Para" })
  )
  const fields = [
    within(card).getByRole("textbox", { name: "Para" }),
    within(card).getByLabelText("Prioridade"),
    within(card).getByLabelText("Story Points"),
  ]
  for (const field of fields) {
    expect(field).toHaveClass("focus-visible:ring-2", "focus-visible:ring-ring")
    expect(field.className).not.toMatch(/ring-ring\/|ring-3/)
  }
  expect(fields[1]).toHaveClass("h-10")
  expect(container.querySelector('[data-slot="notice"]')).toBeNull()
})
