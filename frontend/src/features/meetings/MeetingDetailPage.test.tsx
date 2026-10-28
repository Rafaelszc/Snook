import { act, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { axe } from "vitest-axe"

import { POLL_INTERVAL_MS } from "@/lib/poll"
import { server } from "@/test/server"

import type { MeetingDetail } from "./api"
import { detail, MEETING_ID } from "./fixtures"
import { renderMeetings } from "./testing"

const URL = `/api/meetings/${MEETING_ID}`
const PATH = `/meetings/${MEETING_ID}`

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
afterEach(() => vi.useRealTimers())

function detailSequence(...items: MeetingDetail[]) {
  let calls = 0
  server.use(
    http.get(URL, () =>
      HttpResponse.json(items[Math.min(calls++, items.length - 1)])
    )
  )
  return () => calls
}

const tick = () => act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS))

it("mostra título, status, arquivo e duração sem caminho interno", async () => {
  detailSequence(detail({ status: "done" }))
  const { container } = renderMeetings(PATH)

  expect(
    await screen.findByRole("heading", { name: "Planejamento do trimestre" })
  ).toBeVisible()
  expect(screen.getByRole("status")).toHaveTextContent("Concluída")
  expect(screen.getByText("planejamento.mp3")).toBeVisible()
  expect(screen.getByText("1:02:05")).toBeVisible()
  expect(await axe(container)).toHaveNoViolations()
})

it("anuncia a troca de status em aria-live e para o polling no fim (meetings 40)", async () => {
  const calls = detailSequence(
    detail({ status: "processing" }),
    detail({ status: "transcribed", participants_confirmed: true }),
    detail({ status: "generating" }),
    detail({ status: "done" })
  )
  renderMeetings(PATH)

  const badge = await screen.findByText("Processando")
  expect(badge).toHaveAttribute("aria-live", "polite")
  await tick()
  expect(await screen.findByText("Transcrita")).toBeVisible()
  await tick()
  expect(await screen.findByText("Gerando backlog")).toBeVisible()
  await tick()
  expect(await screen.findByText("Concluída")).toBeVisible()

  const settled = calls()
  await tick()
  await tick()
  expect(calls()).toBe(settled)
})

it("transcrita sem nomes confirmados não faz polling (meetings 40)", async () => {
  const calls = detailSequence(detail({ status: "transcribed" }))
  renderMeetings(PATH)
  await screen.findByText("Transcrita")
  await tick()
  await tick()
  expect(calls()).toBe(1)
})

it("edita o título (meetings 41)", async () => {
  detailSequence(detail({ status: "done" }))
  let body: unknown = null
  server.use(
    http.patch(URL, async ({ request }) => {
      body = await request.json()
      return HttpResponse.json(detail({ status: "done", title: "Novo título" }))
    })
  )
  renderMeetings(PATH)
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

  await user.click(await screen.findByRole("button", { name: "Editar título" }))
  const field = screen.getByLabelText("Título")
  await user.clear(field)
  await user.type(field, "Novo título")
  await user.click(screen.getByRole("button", { name: "Salvar" }))

  expect(
    await screen.findByRole("heading", { name: "Novo título" })
  ).toBeVisible()
  expect(body).toEqual({ title: "Novo título" })
})

it("título inválido mostra o erro da API no campo", async () => {
  detailSequence(detail({ status: "done" }))
  server.use(
    http.patch(URL, () =>
      HttpResponse.json(
        {
          error: {
            code: "validation_error",
            message: "Dados inválidos.",
            fields: { title: "Informe um título." },
          },
        },
        { status: 422 }
      )
    )
  )
  renderMeetings(PATH)
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

  await user.click(await screen.findByRole("button", { name: "Editar título" }))
  await user.clear(screen.getByLabelText("Título"))
  await user.click(screen.getByRole("button", { name: "Salvar" }))

  await waitFor(() =>
    expect(screen.getByLabelText("Título")).toHaveAccessibleDescription(
      "Informe um título."
    )
  )
})

it("excluir pede confirmação, avisa o que se apaga e volta à lista (meetings 43)", async () => {
  detailSequence(detail({ status: "done" }))
  let deleted = false
  server.use(
    http.delete(URL, () => {
      deleted = true
      return new HttpResponse(null, { status: 204 })
    })
  )
  const { router } = renderMeetings(PATH)
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

  await user.click(await screen.findByRole("button", { name: "Excluir" }))
  const dialog = screen.getByRole("alertdialog", { name: "Excluir reunião?" })
  expect(dialog).toHaveAccessibleDescription(/áudio.*backlog.*apagados/)
  expect(dialog).toHaveAttribute("data-slot", "glass-panel")
  expect(await axe(dialog)).toHaveNoViolations()
  expect(deleted).toBe(false)

  await user.click(screen.getByRole("button", { name: "Excluir reunião" }))

  await waitFor(() => expect(router.state.location.pathname).toBe("/"))
  expect(deleted).toBe(true)
})

it("cancelar a exclusão não chama a API", async () => {
  detailSequence(detail({ status: "done" }))
  renderMeetings(PATH)
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

  await user.click(await screen.findByRole("button", { name: "Excluir" }))
  await user.click(screen.getByRole("button", { name: "Cancelar" }))

  expect(screen.queryByRole("alertdialog")).toBeNull()
})

it("id inexistente ou de outro usuário mostra não encontrada", async () => {
  server.use(
    http.get(URL, () =>
      HttpResponse.json(
        {
          error: {
            code: "meeting_not_found",
            message: "Reunião não encontrada.",
          },
        },
        { status: 404 }
      )
    )
  )
  renderMeetings(PATH)
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Reunião não encontrada."
  )
})

it("em transcribed sem nomes, leva à tela de nomeação (participants 25)", async () => {
  detailSequence(detail({ status: "transcribed" }))
  const { container, router } = renderMeetings(PATH)

  const link = await screen.findByRole("link", {
    name: "Nomear participantes",
  })
  expect(await axe(container)).toHaveNoViolations()
  await userEvent.click(link)
  expect(router.state.location.pathname).toBe(`${PATH}/participants`)
})

it("em needs_split, leva à tela de divisão (transcript-split 30)", async () => {
  detailSequence(
    detail({ status: "needs_split", participants_confirmed: true })
  )
  const { container, router } = renderMeetings(PATH)

  const link = await screen.findByRole("link", { name: "Dividir reunião" })
  expect(await axe(container)).toHaveNoViolations()
  await userEvent.click(link)
  expect(router.state.location.pathname).toBe(`${PATH}/split`)
})

it("fora de needs_split, não oferece divisão", async () => {
  detailSequence(detail({ status: "done", participants_confirmed: true }))
  renderMeetings(PATH)

  expect(await screen.findByText("Concluída")).toBeVisible()
  expect(
    screen.queryByRole("link", { name: "Dividir reunião" })
  ).not.toBeInTheDocument()
})

it("com nomes confirmados ou em outro status, não oferece nomeação", async () => {
  detailSequence(
    detail({ status: "transcribed", participants_confirmed: true })
  )
  renderMeetings(PATH)

  expect(await screen.findByText("Transcrita")).toBeVisible()
  expect(
    screen.queryByRole("link", { name: "Nomear participantes" })
  ).not.toBeInTheDocument()
})
