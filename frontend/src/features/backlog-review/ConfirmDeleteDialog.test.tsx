import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import {
  backlog,
  meeting,
  record,
  renderReview,
  serve,
  story,
  TWO_EPICS,
} from "./testing"

async function ready() {
  serve(meeting())
  const view = renderReview()
  await screen.findByRole("article", { name: "Cadastrar cliente" })
  return view
}

it("excluir US pede confirmação antes de chamar a API (backlog-review 42)", async () => {
  const calls = record("delete", "/user-stories/11")
  await ready()
  const card = screen.getByRole("article", { name: "Cadastrar cliente" })

  await userEvent.click(
    within(card).getByRole("button", { name: "Excluir User Story" })
  )
  const dialog = await screen.findByRole("alertdialog", {
    name: "Excluir US-01?",
  })
  expect(calls).toEqual([])
  expect(await axe(document.body)).toHaveNoViolations()
  await userEvent.click(within(dialog).getByRole("button", { name: "Excluir" }))

  await waitFor(() => expect(calls).toHaveLength(1))
})

it("cancelar a confirmação não exclui (backlog-review 42)", async () => {
  const calls = record("delete", "/criteria/101")
  serve(
    meeting(),
    backlog([
      {
        id: 1,
        name: "Cadastro",
        user_stories: [
          story({
            acceptance_criteria: [
              { id: 101, given: "a", when: "b", then: "c" },
              { id: 102, given: "d", when: "e", then: "f" },
            ],
          }),
        ],
      },
    ])
  )
  renderReview()

  const [first] = await screen.findAllByRole("button", {
    name: "Excluir critério",
  })
  await userEvent.click(first)
  await userEvent.click(
    within(await screen.findByRole("alertdialog")).getByRole("button", {
      name: "Cancelar",
    })
  )

  expect(calls).toEqual([])
})

it("Epic com US tem excluir desabilitado; vazia exclui com confirmação (backlog-review 42)", async () => {
  const calls = record("delete", "/epics/2")
  await ready()

  const blocked = screen.getByRole("button", { name: "Excluir Epic Cadastro" })
  expect(blocked).toBeDisabled()
  expect(blocked).toHaveAccessibleDescription(
    "Só é possível excluir uma Epic sem User Stories."
  )
  await userEvent.click(
    screen.getByRole("button", { name: "Excluir Epic Relatórios" })
  )
  await userEvent.click(
    within(await screen.findByRole("alertdialog")).getByRole("button", {
      name: "Excluir",
    })
  )

  await waitFor(() => expect(calls).toHaveLength(1))
})

it("último critério não pode ser excluído", async () => {
  await ready()
  const card = screen.getByRole("article", { name: "Cadastrar cliente" })

  expect(
    within(card).getByRole("button", { name: "Excluir critério" })
  ).toBeDisabled()
})

it("renomear Epic para nome existente avisa da junção antes de salvar (backlog-review 41)", async () => {
  const calls = record("patch", "/epics/2")
  await ready()

  await userEvent.click(
    screen.getByRole("button", { name: "Editar Nome da Epic Relatórios" })
  )
  const input = screen.getByRole("textbox", { name: "Nome da Epic Relatórios" })
  await userEvent.clear(input)
  await userEvent.type(input, "  cadastro ")

  expect(
    screen.getByText(
      'Já existe a Epic "Cadastro". Ao salvar, as duas serão juntadas.'
    )
  ).toHaveAttribute("role", "status")
  expect(input).toHaveAccessibleDescription(/as duas serão juntadas/)
  expect(calls).toEqual([])
  await userEvent.type(input, "{Enter}")
  await waitFor(() => expect(calls).toEqual([{ name: "  cadastro " }]))
})

it("criar Epic com nome existente avisa da junção (backlog-review 41)", async () => {
  const calls = record("post", "/epics")
  await ready()

  const input = screen.getByLabelText("Nova Epic")
  await userEvent.type(input, "RELATÓRIOS")
  expect(
    screen.getByText(
      'Já existe a Epic "Relatórios". Ao salvar, as duas serão juntadas.'
    )
  ).toBeInTheDocument()
  await userEvent.click(screen.getByRole("button", { name: "Criar Epic" }))

  await waitFor(() => expect(calls).toEqual([{ name: "RELATÓRIOS" }]))
  await waitFor(() => expect(input).toHaveValue(""))
})

it("mover US abre a escolha entre as outras Epics (backlog-review 43)", async () => {
  const calls = record("patch", "/user-stories/11")
  serve(
    meeting(),
    backlog([...TWO_EPICS, { id: 3, name: "Financeiro", user_stories: [] }])
  )
  renderReview()
  const card = await screen.findByRole("article", { name: "Cadastrar cliente" })

  await userEvent.click(within(card).getByRole("button", { name: "Mover" }))
  const dialog = await screen.findByRole("dialog", {
    name: "Mover US-01 para outra Epic",
  })
  const options = within(dialog).getAllByRole("radio")
  expect(options.map((o) => o.closest("label")?.textContent)).toEqual([
    "Relatórios",
    "Financeiro",
  ])
  await userEvent.click(
    within(dialog).getByRole("radio", { name: "Financeiro" })
  )
  expect(await axe(document.body)).toHaveNoViolations()
  await userEvent.click(within(dialog).getByRole("button", { name: "Mover" }))

  await waitFor(() => expect(calls).toEqual([{ epic_id: 3 }]))
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  )
})

it("cria US na Epic com um critério e mostra erro do campo (backlog-review 17, 40)", async () => {
  const calls = record(
    "post",
    "/epics/2/user-stories",
    () =>
      new Response(
        JSON.stringify({
          error: {
            code: "validation_error",
            message: "Dados inválidos.",
            fields: { "acceptance_criteria.0.then": "Preencha este campo." },
          },
        }),
        { status: 422, headers: { "Content-Type": "application/json" } }
      )
  )
  await ready()
  const section = screen.getByRole("region", { name: /Relatórios/ })

  await userEvent.click(
    within(section).getByRole("button", { name: "Nova User Story" })
  )
  const form = within(section).getByRole("form", { name: "Nova User Story" })
  await userEvent.type(
    within(form).getByLabelText("Nome da User Story"),
    "Exportar vendas"
  )
  await userEvent.type(within(form).getByLabelText("Como"), "gerente")
  await userEvent.type(
    within(form).getByLabelText("Eu quero"),
    "exportar vendas"
  )
  await userEvent.type(within(form).getByLabelText("Para"), "fechar o mês")
  await userEvent.selectOptions(within(form).getByLabelText("Solicitante"), "2")
  const criterion = within(form).getByRole("group", {
    name: "Critérios de aceitação",
  })
  await userEvent.type(
    within(criterion).getByLabelText("Dado"),
    "vendas no mês"
  )
  await userEvent.type(within(criterion).getByLabelText("Quando"), "exporto")
  await userEvent.click(
    within(form).getByRole("button", { name: "Criar User Story" })
  )

  expect(
    await within(form).findByText("Preencha este campo.")
  ).toBeInTheDocument()
  expect(calls).toEqual([
    {
      name: "Exportar vendas",
      as_a: "gerente",
      i_want: "exportar vendas",
      so_that: "fechar o mês",
      priority: "Medium",
      story_points: 3,
      requested_by: 2,
      requested_at: null,
      acceptance_criteria: [
        { given: "vendas no mês", when: "exporto", then: "" },
      ],
    },
  ])
})
