import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { axe } from "vitest-axe"

import { server } from "@/test/server"

import type { LlmConfigState, MeetingNamingState, Speaker } from "./api"
import { NamingPage } from "./NamingPage"

const ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"

const SPEAKERS: Speaker[] = [
  { speaker_label: "SPEAKER_00", total_seconds: 245 },
  { speaker_label: "SPEAKER_01", total_seconds: 3725.4 },
  { speaker_label: "SPEAKER_02", total_seconds: 12 },
]

const ACTIVE: LlmConfigState[] = [
  { provider: "openai", state: "configured", model: "gpt-5-mini" },
  { provider: "anthropic", state: "active", model: "claude-sonnet-4-5" },
]
const NONE: LlmConfigState[] = [
  { provider: "openai", state: "configured", model: "gpt-5-mini" },
]

const transcribed: MeetingNamingState = {
  status: "transcribed",
  participants_confirmed: false,
}

let play: ReturnType<typeof vi.fn<() => Promise<void>>>
let pause: ReturnType<typeof vi.fn<() => void>>

// jsdom não toca mídia.
beforeEach(() => {
  play = vi.fn<() => Promise<void>>(() => Promise.resolve())
  pause = vi.fn<() => void>()
  vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(play)
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(pause)
})
afterEach(() => vi.restoreAllMocks())

function serve({
  meeting = transcribed,
  configs = ACTIVE,
}: { meeting?: MeetingNamingState; configs?: LlmConfigState[] } = {}) {
  server.use(
    http.get(`/api/meetings/${ID}`, () => HttpResponse.json(meeting)),
    http.get(`/api/meetings/${ID}/speakers`, () => HttpResponse.json(SPEAKERS)),
    http.get("/api/llm-configs", () => HttpResponse.json(configs))
  )
}

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/meetings/:id/participants", element: <NamingPage /> },
      { path: "/meetings/:id", element: <p>detalhe</p> },
      { path: "/settings", element: <p>configurações</p> },
    ],
    { initialEntries: [`/meetings/${ID}/participants`] }
  )
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
  return { ...view, router }
}

const confirmButton = () =>
  screen.getByRole("button", { name: "Confirmar nomes" })

async function fillAll(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText("Nome de SPEAKER_00"), "Ana")
  await user.type(screen.getByLabelText("Nome de SPEAKER_01"), "Bruno")
  await user.type(screen.getByLabelText("Nome de SPEAKER_02"), "Carla")
}

it("mostra amostra, tempo de fala e campo de nome por speaker (26)", async () => {
  serve()
  const { container } = renderPage()

  const list = await screen.findByRole("list", { name: "Vozes da reunião" })
  const rows = within(list).getAllByRole("listitem")
  expect(rows).toHaveLength(3)
  expect(
    within(rows[0]).getByRole("button", { name: "Ouvir amostra de SPEAKER_00" })
  ).toBeVisible()
  expect(within(rows[0]).getByText("4:05")).toBeVisible()
  expect(within(rows[1]).getByText("1:02:05")).toBeVisible()
  expect(within(rows[2]).getByText("0:12")).toBeVisible()
  expect(screen.getByLabelText("Nome de SPEAKER_02")).toHaveValue("")
  expect(await axe(container)).toHaveNoViolations()
})

it("toca e pausa a amostra pelo teclado, uma por vez", async () => {
  serve()
  const user = userEvent.setup()
  const { container } = renderPage()

  const first = await screen.findByRole("button", {
    name: "Ouvir amostra de SPEAKER_00",
  })
  first.focus()
  await user.keyboard("{Enter}")
  expect(play).toHaveBeenCalledTimes(1)
  const audio = container.querySelector("audio")
  expect(audio?.getAttribute("src")).toBe(
    `/api/meetings/${ID}/speakers/SPEAKER_00/sample`
  )
  const pauseButton = screen.getByRole("button", {
    name: "Pausar amostra de SPEAKER_00",
  })
  expect(pauseButton).toHaveAttribute("aria-pressed", "true")
  expect(pauseButton).toHaveFocus()

  await user.click(
    screen.getByRole("button", { name: "Ouvir amostra de SPEAKER_01" })
  )
  expect(audio?.getAttribute("src")).toContain("SPEAKER_01")
  expect(
    screen.getByRole("button", { name: "Ouvir amostra de SPEAKER_00" })
  ).toHaveAttribute("aria-pressed", "false")

  await user.click(
    screen.getByRole("button", { name: "Pausar amostra de SPEAKER_01" })
  )
  expect(pause).toHaveBeenCalled()
})

it("avisa quando a amostra não toca", async () => {
  serve()
  play.mockImplementation(() => Promise.reject(new Error("x")))
  const user = userEvent.setup()
  renderPage()

  await user.click(
    await screen.findByRole("button", { name: "Ouvir amostra de SPEAKER_00" })
  )
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Não foi possível tocar a amostra."
  )
})

it("desabilita confirmar enquanto algum speaker está sem nome (30)", async () => {
  serve()
  const user = userEvent.setup()
  renderPage()

  await user.type(await screen.findByLabelText("Nome de SPEAKER_00"), "Ana")
  await user.type(screen.getByLabelText("Nome de SPEAKER_01"), "Bruno")
  await user.type(screen.getByLabelText("Nome de SPEAKER_02"), "   ")
  expect(confirmButton()).toBeDisabled()
  expect(
    screen.getByText("Dê um nome a cada voz para confirmar.")
  ).toBeVisible()

  await user.type(screen.getByLabelText("Nome de SPEAKER_02"), "Carla")
  expect(confirmButton()).toBeEnabled()
  expect(screen.getByText("3 vozes, 3 participantes")).toBeVisible()
})

it("indica que speakers com o mesmo nome serão juntados (27)", async () => {
  serve()
  const user = userEvent.setup()
  renderPage()

  await user.type(await screen.findByLabelText("Nome de SPEAKER_00"), "Ana")
  await user.type(screen.getByLabelText("Nome de SPEAKER_01"), "Bruno")
  await user.type(screen.getByLabelText("Nome de SPEAKER_02"), "  ana ")

  expect(
    screen.getByLabelText("Nome de SPEAKER_00")
  ).toHaveAccessibleDescription(
    "Mesmo nome de SPEAKER_02: serão juntados num só participante."
  )
  expect(
    screen.getByLabelText("Nome de SPEAKER_02")
  ).toHaveAccessibleDescription(
    "Mesmo nome de SPEAKER_00: serão juntados num só participante."
  )
  expect(
    screen.getByLabelText("Nome de SPEAKER_01")
  ).not.toHaveAccessibleDescription()
  expect(screen.getByText("3 vozes, 2 participantes")).toBeVisible()
})

it("mostra o provedor ativo e o modelo da geração (28)", async () => {
  serve()
  renderPage()

  expect(
    await screen.findByText("Usará Anthropic, modelo claude-sonnet-4-5.")
  ).toBeVisible()
})

it("sem provedor ativo, avisa com link para configurações e bloqueia (29)", async () => {
  serve({ configs: NONE })
  const user = userEvent.setup()
  const { container, router } = renderPage()

  await fillAll(user)
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Nenhum provedor de LLM ativo."
  )
  expect(confirmButton()).toBeDisabled()
  expect(await axe(container)).toHaveNoViolations()

  await user.click(screen.getByRole("link", { name: "Abrir configurações" }))
  expect(router.state.location.pathname).toBe("/settings")
})

it("confirma os nomes e leva ao detalhe da reunião (31)", async () => {
  serve()
  let body: unknown
  server.use(
    http.put(`/api/meetings/${ID}/participants`, async ({ request }) => {
      body = await request.json()
      return HttpResponse.json([
        { id: 1, name: "Ana", speaker_labels: ["SPEAKER_00", "SPEAKER_02"] },
        { id: 2, name: "Bruno", speaker_labels: ["SPEAKER_01"] },
      ])
    })
  )
  const user = userEvent.setup()
  const { router } = renderPage()

  await user.type(await screen.findByLabelText("Nome de SPEAKER_00"), "Ana")
  await user.type(screen.getByLabelText("Nome de SPEAKER_01"), "Bruno")
  await user.type(screen.getByLabelText("Nome de SPEAKER_02"), "ana")
  await user.click(confirmButton())

  expect(await screen.findByText("detalhe")).toBeVisible()
  expect(router.state.location.pathname).toBe(`/meetings/${ID}`)
  expect(body).toEqual({
    names: { SPEAKER_00: "Ana", SPEAKER_01: "Bruno", SPEAKER_02: "ana" },
  })
})

it("mostra o erro da API e fica na tela", async () => {
  serve()
  server.use(
    http.put(`/api/meetings/${ID}/participants`, () =>
      HttpResponse.json(
        {
          error: {
            code: "validation_error",
            message: "Dê um nome a cada voz da reunião.",
            fields: { "names.SPEAKER_01": "Dê um nome a esta voz." },
          },
        },
        { status: 422 }
      )
    )
  )
  const user = userEvent.setup()
  const { router } = renderPage()

  await fillAll(user)
  await user.click(confirmButton())

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Dê um nome a cada voz da reunião."
  )
  expect(
    screen.getByLabelText("Nome de SPEAKER_01")
  ).toHaveAccessibleDescription("Dê um nome a esta voz.")
  expect(screen.getByLabelText("Nome de SPEAKER_01")).toHaveFocus()
  expect(router.state.location.pathname).toBe(`/meetings/${ID}/participants`)
})

it("fora de transcribed ou já confirmada, não mostra o formulário", async () => {
  serve({ meeting: { status: "transcribed", participants_confirmed: true } })
  renderPage()

  expect(
    await screen.findByText(/Esta reunião não está esperando nomes/)
  ).toBeVisible()
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument()
})

it("reunião de outro usuário ou inexistente: não encontrada", async () => {
  serve()
  server.use(
    http.get(`/api/meetings/${ID}`, () =>
      HttpResponse.json(
        { error: { code: "meeting_not_found", message: "x" } },
        { status: 404 }
      )
    )
  )
  renderPage()

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Reunião não encontrada."
  )
})
