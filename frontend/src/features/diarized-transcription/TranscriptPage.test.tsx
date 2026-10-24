import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { beforeAll, expect, it } from "vitest"
import { axe } from "vitest-axe"

import { server } from "@/test/server"

import type { MeetingStatus, Participant, Transcript } from "./api"
import { transcript2h, TRANSCRIPT_2H_COUNT } from "./fixtures/transcript-2h"
import { TranscriptPage } from "./TranscriptPage"

const ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
const VIEWPORT_PX = 600

// jsdom não tem layout: dá altura ao contêiner rolável e às linhas.
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get() {
      return this.getAttribute("role") === "region" ? VIEWPORT_PX : 72
    },
  })
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get: () => 800,
  })
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    get: () => 72,
  })
})

function serve(
  meeting: MeetingStatus,
  transcript?: Transcript,
  participants?: Participant[] | 404
) {
  server.use(
    http.get(`/api/meetings/${ID}/participants`, () =>
      participants === undefined || participants === 404
        ? HttpResponse.json(
            { error: { code: "meeting_not_found", message: "x" } },
            { status: 404 }
          )
        : HttpResponse.json(participants)
    ),
    http.get(`/api/meetings/${ID}`, () => HttpResponse.json(meeting)),
    http.get(`/api/meetings/${ID}/transcript`, () =>
      transcript
        ? HttpResponse.json(transcript)
        : HttpResponse.json(
            { error: { code: "transcript_not_ready", message: "x" } },
            { status: 409 }
          )
    )
  )
}

function renderPage() {
  const router = createMemoryRouter(
    [{ path: "/meetings/:id/transcript", element: <TranscriptPage /> }],
    { initialEntries: [`/meetings/${ID}/transcript`] }
  )
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}

const done: MeetingStatus = { status: "done", failed_stage: null }

it("mostra segmentos em ordem com instante hh:mm:ss, speaker e texto (25)", async () => {
  serve(done, {
    segments: [
      {
        id: 1,
        speaker_label: "SPEAKER_00",
        start_seconds: 0.5,
        end_seconds: 4.5,
        text: "Bom dia.",
      },
      {
        id: 2,
        speaker_label: "SPEAKER_01",
        start_seconds: 3725,
        end_seconds: 3730,
        text: "Segue o relatório.",
      },
    ],
  })
  const { container } = renderPage()

  const items = await screen.findAllByRole("listitem")
  expect(items).toHaveLength(2)
  expect(within(items[0]).getByText("00:00:00")).toBeVisible()
  expect(within(items[0]).getByText("SPEAKER_00")).toBeVisible()
  expect(within(items[0]).getByText("Bom dia.")).toBeVisible()
  expect(within(items[1]).getByText("01:02:05")).toBeVisible()
  expect(await axe(container)).toHaveNoViolations()
})

it("antes de transcribed mostra o status, não o texto (27)", async () => {
  serve({ status: "processing", failed_stage: null })
  renderPage()

  expect(await screen.findByText("Processando")).toBeVisible()
  expect(screen.getByText("A transcrição ainda não está pronta.")).toBeVisible()
  expect(screen.queryByRole("listitem")).not.toBeInTheDocument()
})

it("falha na transcrição mostra o status", async () => {
  serve({ status: "failed", failed_stage: "transcription" })
  renderPage()

  expect(
    await screen.findByText("A transcrição ainda não está pronta.")
  ).toBeVisible()
})

it("2 h de fixture: só os segmentos perto da área visível no DOM (31)", async () => {
  serve(done, transcript2h())
  renderPage()

  await screen.findAllByRole("listitem")
  const rendered = screen.getAllByRole("listitem").length
  expect(rendered).toBeGreaterThan(0)
  expect(rendered).toBeLessThan(60)
  expect(rendered).toBeLessThan(TRANSCRIPT_2H_COUNT / 10)
})

it("rolar até o fim mostra o último segmento (31)", async () => {
  serve(done, transcript2h())
  renderPage()

  const region = await screen.findByRole("region")
  await screen.findAllByRole("listitem")
  region.scrollTop = TRANSCRIPT_2H_COUNT * 72
  region.dispatchEvent(new Event("scroll"))

  const last = await screen.findByText(
    `Trecho número ${TRANSCRIPT_2H_COUNT} da reunião.`
  )
  const item = last.closest("li")!
  expect(within(item).getByText("01:59:54")).toBeVisible()
  expect(within(item).getByText("SPEAKER_01")).toBeVisible()
})

it("renderiza texto de segmento escapado (SEC-12)", async () => {
  serve(done, {
    segments: [
      {
        id: 1,
        speaker_label: "SPEAKER_00",
        start_seconds: 0,
        end_seconds: 1,
        text: '<img src=x onerror="alert(1)">',
      },
    ],
  })
  const { container } = renderPage()

  expect(
    await screen.findByText('<img src=x onerror="alert(1)">')
  ).toBeVisible()
  expect(container.querySelector("img")).toBeNull()
})

const ONE_SEGMENT: Transcript = {
  segments: [
    {
      id: 1,
      speaker_label: "SPEAKER_00",
      start_seconds: 0,
      end_seconds: 1,
      text: "Bom dia.",
    },
  ],
}

it("sem nomes (404), mostra o rótulo e não quebra (26)", async () => {
  serve(done, ONE_SEGMENT, 404)
  renderPage()

  expect(await screen.findByText("SPEAKER_00")).toBeVisible()
})

it("lista vazia de Participantes mostra o rótulo (26)", async () => {
  serve(done, ONE_SEGMENT, [])
  renderPage()

  expect(await screen.findByText("SPEAKER_00")).toBeVisible()
})

it("com Participante nomeado, mostra o nome atual no lugar do rótulo (26)", async () => {
  serve(done, ONE_SEGMENT, [
    { id: "p1", name: "Ana", speaker_labels: ["SPEAKER_00"] },
  ])
  renderPage()

  expect(await screen.findByText("Ana")).toBeVisible()
  expect(screen.queryByText("SPEAKER_00")).not.toBeInTheDocument()
})

it("nome renomeado aparece ao reabrir a tela, sem passo extra (26)", async () => {
  serve(done, ONE_SEGMENT, [
    { id: "p1", name: "Ana", speaker_labels: ["SPEAKER_00"] },
  ])
  const first = renderPage()
  expect(await screen.findByText("Ana")).toBeVisible()
  first.unmount()

  serve(done, ONE_SEGMENT, [
    { id: "p1", name: "Ana Souza", speaker_labels: ["SPEAKER_00"] },
  ])
  renderPage()

  expect(await screen.findByText("Ana Souza")).toBeVisible()
})
