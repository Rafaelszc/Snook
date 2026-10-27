import { act, screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { axe } from "vitest-axe"

import { POLL_INTERVAL_MS } from "@/lib/poll"
import { server } from "@/test/server"

import type { MeetingSummary } from "./api"
import { SUMMARY } from "./fixtures"
import { renderMeetings } from "./testing"

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
afterEach(() => vi.useRealTimers())

// Cada GET devolve o próximo da fila; o último se repete.
function listSequence(...lists: MeetingSummary[][]) {
  let calls = 0
  server.use(
    http.get("/api/meetings", () =>
      HttpResponse.json(lists[Math.min(calls++, lists.length - 1)])
    )
  )
  return () => calls
}

const tick = () => act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS))

it("lista título, data, duração e status, com link ao detalhe", async () => {
  listSequence([{ ...SUMMARY, status: "done" }])
  const { container } = renderMeetings("/")

  const link = await screen.findByRole("link", { name: SUMMARY.title })
  expect(link).toHaveAttribute("href", `/meetings/${SUMMARY.id}`)
  const row = link.closest("li") as HTMLElement
  expect(within(row).getByText(/1:02:05/)).toBeVisible()
  expect(within(row).getByRole("status")).toHaveTextContent("Concluída")
  expect(await axe(container)).toHaveNoViolations()
})

it("lista vazia convida a enviar", async () => {
  listSequence([])
  renderMeetings("/")
  expect(await screen.findByText("Nenhuma reunião ainda.")).toBeVisible()
  expect(screen.getByRole("link", { name: "Nova reunião" })).toHaveAttribute(
    "href",
    "/meetings/new"
  )
})

it("oferece as duas entradas: enviar arquivo e gravar (screen-recording 1)", async () => {
  listSequence([])
  renderMeetings("/")
  await screen.findByText("Nenhuma reunião ainda.")
  expect(screen.getByRole("link", { name: "Gravar reunião" })).toHaveAttribute(
    "href",
    "/meetings/record"
  )
})

it("atualiza o status sozinha enquanto há trabalho em andamento (meetings 40)", async () => {
  const calls = listSequence(
    [{ ...SUMMARY, status: "pending" }],
    [{ ...SUMMARY, status: "processing" }],
    [{ ...SUMMARY, status: "done" }]
  )
  renderMeetings("/")

  expect(await screen.findByText("Pendente")).toBeVisible()
  await tick()
  expect(await screen.findByText("Processando")).toBeVisible()
  await tick()
  expect(await screen.findByText("Concluída")).toBeVisible()

  const settled = calls()
  await tick()
  await tick()
  expect(calls()).toBe(settled)
})

it("faz polling em transcrita com nomes confirmados (meetings 40)", async () => {
  const calls = listSequence(
    [{ ...SUMMARY, status: "transcribed", participants_confirmed: true }],
    [{ ...SUMMARY, status: "generating", participants_confirmed: true }]
  )
  renderMeetings("/")

  expect(await screen.findByText("Transcrita")).toBeVisible()
  await tick()
  expect(await screen.findByText("Gerando backlog")).toBeVisible()
  expect(calls()).toBeGreaterThanOrEqual(2)
})

it.each(["transcribed", "needs_split", "done", "failed"] as const)(
  "sem polling com status %s (meetings 40)",
  async (status) => {
    const calls = listSequence([{ ...SUMMARY, status }])
    renderMeetings("/")
    await screen.findByRole("link", { name: SUMMARY.title })
    await tick()
    await tick()
    expect(calls()).toBe(1)
  }
)
