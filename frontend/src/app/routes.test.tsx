import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { routes } from "./routes"
import { NOT_CONFIGURED } from "@/features/llm-providers/fixtures"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

const ANA = { id: "u1", email: "ana@x.com", username: "ana" }

function signedIn() {
  server.use(
    http.get("/api/auth/me", () => HttpResponse.json(ANA)),
    http.get("/api/llm-configs", () => HttpResponse.json(NOT_CONFIGURED))
  )
}

function signedOut() {
  server.use(
    http.get("/api/auth/me", () =>
      HttpResponse.json(
        {
          error: {
            code: "not_authenticated",
            message: "Faça login para continuar.",
          },
        },
        { status: 401 }
      )
    )
  )
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return renderWithProviders(<RouterProvider router={router} />)
}

it("navega entre rotas placeholder pelo layout", async () => {
  signedIn()
  const { container } = renderAt("/")
  expect(
    await screen.findByRole("heading", { name: "Reuniões" })
  ).toBeInTheDocument()
  await userEvent.click(screen.getByRole("link", { name: "Configurações" }))
  expect(
    screen.getByRole("heading", { name: "Configurações" })
  ).toBeInTheDocument()
  expect(await axe(container)).toHaveNoViolations()
})

it("página protegida sem sessão leva ao login (auth 24)", async () => {
  signedOut()
  renderAt("/settings")
  expect(
    await screen.findByRole("heading", { name: "Entrar" })
  ).toBeInTheDocument()
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument()
})

it("depois do logout volta ao login (auth 26)", async () => {
  signedIn()
  let loggedOut = false
  server.use(
    http.post("/api/auth/logout", () => {
      loggedOut = true
      return new HttpResponse(null, { status: 204 })
    })
  )
  renderAt("/")
  await userEvent.click(await screen.findByRole("button", { name: "Sair" }))
  expect(
    await screen.findByRole("heading", { name: "Entrar" })
  ).toBeInTheDocument()
  expect(loggedOut).toBe(true)
})

it("login e cadastro ficam fora do layout autenticado", () => {
  renderAt("/login")
  expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument()
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument()
})

it("rota desconhecida mostra não encontrada", async () => {
  signedIn()
  renderAt("/nada")
  expect(
    await screen.findByRole("heading", { name: "Página não encontrada" })
  ).toBeInTheDocument()
})

it("o ConsentNotice ainda não existe (Task 22.1)", async () => {
  signedIn()
  renderAt("/")
  await screen.findByRole("heading", { name: "Reuniões" })
  expect(screen.queryByTestId("consent-notice")).not.toBeInTheDocument()
})
