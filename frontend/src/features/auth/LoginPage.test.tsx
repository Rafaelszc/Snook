import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { afterEach, expect, it, vi } from "vitest"
import { axe } from "vitest-axe"

import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

import { LoginPage } from "./LoginPage"

const INVALID = "Email, nome de usuário ou senha inválidos."

function renderLogin(state?: unknown) {
  const router = createMemoryRouter(
    [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <h1>Criar conta</h1> },
      { path: "/", element: <h1>Reuniões</h1> },
      { path: "/settings", element: <h1>Configurações</h1> },
    ],
    { initialEntries: [{ pathname: "/login", state }] }
  )
  return renderWithProviders(<RouterProvider router={router} />)
}

async function fill(identifier: string, password: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText("Email ou nome de usuário"), identifier)
  await user.type(screen.getByLabelText("Senha"), password)
  await user.click(screen.getByRole("button", { name: "Entrar" }))
}

function loginOk(onBody?: (body: unknown) => void) {
  server.use(
    http.post("/api/auth/login", async ({ request }) => {
      onBody?.(await request.json())
      return HttpResponse.json({
        id: "u1",
        email: "ana@x.com",
        username: "ana",
      })
    })
  )
}

afterEach(() => vi.restoreAllMocks())

it("oferece login e link para o cadastro (auth 22)", async () => {
  renderLogin()
  expect(screen.getByRole("heading", { name: "Entrar" })).toBeVisible()
  await userEvent.click(screen.getByRole("link", { name: "Criar conta" }))
  expect(screen.getByRole("heading", { name: "Criar conta" })).toBeVisible()
})

it("login bem-sucedido leva à área autenticada", async () => {
  let sent: unknown
  loginOk((body) => (sent = body))
  renderLogin()
  await fill("ana", "senha-forte-1")
  expect(await screen.findByRole("heading", { name: "Reuniões" })).toBeVisible()
  expect(sent).toEqual({ identifier: "ana", password: "senha-forte-1" })
})

it("volta à página protegida que pediu o login (auth 24)", async () => {
  loginOk()
  renderLogin({ from: "/settings" })
  await fill("ana", "senha-forte-1")
  expect(
    await screen.findByRole("heading", { name: "Configurações" })
  ).toBeVisible()
})

it("mostra o erro de login da API (auth 25)", async () => {
  server.use(
    http.post("/api/auth/login", () =>
      HttpResponse.json(
        { error: { code: "invalid_credentials", message: INVALID } },
        { status: 401 }
      )
    )
  )
  const { container } = renderLogin()
  await fill("ana", "senha-errada-1")
  expect(await screen.findByRole("alert")).toHaveTextContent(INVALID)
  expect(screen.getByRole("heading", { name: "Entrar" })).toBeVisible()
  expect(await axe(container)).toHaveNoViolations()
})

it("não grava sessão em Web Storage (03-security.md, Never)", async () => {
  const setItem = vi.spyOn(Storage.prototype, "setItem")
  loginOk()
  renderLogin()
  await fill("ana", "senha-forte-1")
  await screen.findByRole("heading", { name: "Reuniões" })
  expect(setItem).not.toHaveBeenCalled()
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})

it("passa no axe sem erro", async () => {
  const { container } = renderLogin()
  expect(await axe(container)).toHaveNoViolations()
})
