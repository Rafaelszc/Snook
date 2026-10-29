import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"

import { server } from "@/test/server"

import type { Backlog, Epic, ReviewMeeting, UserStory } from "./api"
import { ReviewPage } from "./ReviewPage"

export const ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
export const BASE = `/api/meetings/${ID}`

export function meeting(overrides: Partial<ReviewMeeting> = {}): ReviewMeeting {
  return {
    id: ID,
    title: "Planejamento do trimestre",
    status: "done",
    participants_confirmed: true,
    has_backlog: true,
    failed_stage: null,
    error_message: null,
    ...overrides,
  }
}

export function story(overrides: Partial<UserStory> = {}): UserStory {
  return {
    id: 11,
    us_id: "US-01",
    name: "Cadastrar cliente",
    as_a: "atendente",
    i_want: "cadastrar cliente com CPF",
    so_that: "eu possa abrir pedidos",
    priority: "High",
    story_points: 5,
    requested_by: { id: 1, name: "Ana" },
    requested_at: "00:01:05",
    acceptance_criteria: [
      {
        id: 101,
        given: "CPF válido",
        when: "salvo",
        then: "o cliente aparece",
      },
    ],
    ...overrides,
  }
}

export function backlog(
  epics: Epic[],
  overrides: Partial<Backlog> = {}
): Backlog {
  return {
    read_only: false,
    last_generation_failed: false,
    epics,
    ...overrides,
  }
}

export const TWO_EPICS: Epic[] = [
  {
    id: 1,
    name: "Cadastro",
    user_stories: [
      story(),
      story({
        id: 12,
        us_id: "US-02",
        name: "Buscar cliente",
        requested_by: null,
        requested_at: null,
        priority: "Low",
        story_points: 2,
      }),
    ],
  },
  { id: 2, name: "Relatórios", user_stories: [] },
]

export const PARTICIPANTS = [
  { id: 1, name: "Ana", speaker_labels: ["SPEAKER_00"] },
  { id: 2, name: "Bruno", speaker_labels: ["SPEAKER_01"] },
]

export function serve(
  m: ReviewMeeting | { status: number; code: string },
  b?: Backlog | { status: number; code: string }
) {
  const answer = (body: object) =>
    "code" in body && "status" in body && typeof body.status === "number"
      ? HttpResponse.json(
          { error: { code: body.code, message: "Erro da API." } },
          { status: body.status }
        )
      : HttpResponse.json(body)
  server.use(
    http.get(BASE, () => answer(m)),
    http.get(`${BASE}/backlog`, () => answer(b ?? backlog(TWO_EPICS))),
    http.get(`${BASE}/participants`, () => HttpResponse.json(PARTICIPANTS))
  )
}

// Registra corpo e caminho das escritas; resposta `reply` (padrão 200 `{}`).
export function record(
  method: "post" | "patch" | "delete",
  path: string,
  reply: () => Response = () => HttpResponse.json({})
) {
  const calls: unknown[] = []
  server.use(
    http[method](`${BASE}${path}`, async ({ request }) => {
      const text = await request.text()
      calls.push(text ? JSON.parse(text) : null)
      return reply()
    })
  )
  return calls
}

export function fieldError(field: string, message: string) {
  return () =>
    HttpResponse.json(
      {
        error: {
          code: "validation_error",
          message: "Dados inválidos.",
          fields: { [field]: message },
        },
      },
      { status: 422 }
    )
}

export function renderReview() {
  const router = createMemoryRouter(
    [
      { path: "/meetings/:id/backlog", element: <ReviewPage /> },
      { path: "/meetings/:id", element: <p>detalhe</p> },
      { path: "/meetings/:id/split", element: <p>divisão</p> },
    ],
    { initialEntries: [`/meetings/${ID}/backlog`] }
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
