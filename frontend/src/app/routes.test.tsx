import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { routes } from "./routes"
import { CONSENT_NOTICE_TEXT } from "@/components/surfaces/ConsentNotice/messages"
import { NOT_CONFIGURED } from "@/features/llm-providers/fixtures"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

const ANA = { id: "u1", email: "ana@x.com", username: "ana" }

function signedIn() {
  server.use(
    http.get("/api/auth/me", () => HttpResponse.json(ANA)),
    http.get("/api/llm-configs", () => HttpResponse.json(NOT_CONFIGURED)),
    http.get("/api/meetings", () => HttpResponse.json([]))
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

it("navega entre as telas pelo layout", async () => {
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

it("nav mostra Reuniões e Configurações, com a rota atual marcada", async () => {
  signedIn()
  renderAt("/settings")
  const settings = await screen.findByRole("link", { name: "Configurações" })
  expect(settings).toHaveAttribute("aria-current", "page")
  expect(screen.getByRole("link", { name: "Reuniões" })).not.toHaveAttribute(
    "aria-current"
  )
})

it("sessão nunca vai a localStorage nem sessionStorage (SEC-03)", async () => {
  signedIn()
  localStorage.clear()
  renderAt("/")
  await screen.findByText("ana")
  expect(Object.keys(localStorage).filter((k) => k !== "theme")).toEqual([])
  expect(sessionStorage.length).toBe(0)
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

it("o aviso de consentimento aparece no upload", async () => {
  signedIn()
  renderAt("/")
  await userEvent.click(
    await screen.findByRole("link", { name: "Nova reunião" })
  )
  expect(
    await screen.findByRole("heading", { name: "Nova reunião" })
  ).toBeInTheDocument()
  expect(screen.getByTestId("consent-notice")).toHaveTextContent(
    CONSENT_NOTICE_TEXT
  )
})

// jsdom não tem MediaRecorder nem getDisplayMedia: a tela abre com o botão desabilitado.
it("abre a gravação pela rota, sem quebrar em navegador sem as APIs (screen-recording 22)", async () => {
  signedIn()
  renderAt("/meetings/record")
  expect(
    await screen.findByRole("button", { name: "Gravar reunião" })
  ).toBeDisabled()
  expect(screen.getByTestId("consent-notice")).toHaveTextContent(
    CONSENT_NOTICE_TEXT
  )
})

it("revisão do backlog tem rota própria, destino de cancelar divisão", async () => {
  signedIn()
  renderAt("/meetings/m1/backlog")
  expect(
    await screen.findByRole("heading", { name: "Revisão do backlog" })
  ).toBeInTheDocument()
})
