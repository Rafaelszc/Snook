import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { beforeAll } from "vitest"

import { server } from "@/test/server"

import type { SplitState } from "./api"
import { SplitPage } from "./SplitPage"

export const ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
export const VIEWPORT_PX = 600
export const ROW_PX = 112

// jsdom não mede layout: viewport fixa para o virtualizador.
export function stubLayout() {
  beforeAll(() => {
    Object.defineProperty(HTMLElement.prototype, "clientHeight", {
      configurable: true,
      get() {
        return this.getAttribute("role") === "region" ? VIEWPORT_PX : ROW_PX
      },
    })
    Object.defineProperty(HTMLElement.prototype, "clientWidth", {
      configurable: true,
      get: () => 800,
    })
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get: () => ROW_PX,
    })
  })
}

// Quatro falas de 100 tokens, orçamento 250: cortes sugeridos depois da 2ª.
export function smallSplit(overrides: Partial<SplitState> = {}): SplitState {
  return {
    status: "needs_split",
    split_reason: null,
    can_cancel: false,
    read_only: false,
    message: null,
    provider: "anthropic",
    model: "claude-haiku-4-5",
    budget: 250,
    total_tokens: 400,
    segments: [1, 2, 3, 4].map((id, i) => ({
      id,
      start_seconds: i * 60,
      end_seconds: i * 60 + 55,
      participant: i % 2 ? "Bruno" : "Ana",
      text: `Fala ${id}.`,
      tokens: 100,
    })),
    cuts: [2],
    parts: [],
    ...overrides,
  }
}

export function serveRefresh(
  body: SplitState | { status: number; code: string }
) {
  let calls = 0
  server.use(
    http.post(`/api/meetings/${ID}/split/refresh`, () => {
      calls++
      return "code" in body
        ? HttpResponse.json(
            { error: { code: body.code, message: "Erro da API." } },
            { status: body.status }
          )
        : HttpResponse.json(body)
    })
  )
  return () => calls
}

export function renderSplit() {
  const router = createMemoryRouter(
    [
      { path: "/meetings/:id/split", element: <SplitPage /> },
      { path: "/meetings/:id", element: <p>detalhe</p> },
      { path: "/meetings/:id/backlog", element: <p>revisão</p> },
      { path: "/settings", element: <p>configurações</p> },
    ],
    { initialEntries: [`/meetings/${ID}/split`] }
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
