import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

import { RegisterPage } from "./RegisterPage"

function renderRegister() {
  const router = createMemoryRouter(
    [
      { path: "/register", element: <RegisterPage /> },
      { path: "/login", element: <h1>Entrar</h1> },
      { path: "/", element: <h1>Reuniões</h1> },
    ],
    { initialEntries: ["/register"] }
  )
  return renderWithProviders(<RouterProvider router={router} />)
}

async function fill(email: string, username: string, password: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText("Email"), email)
  await user.type(screen.getByLabelText("Nome de usuário"), username)
  await user.type(screen.getByLabelText("Senha"), password)
  await user.click(screen.getByRole("button", { name: "Criar conta" }))
}

it("oferece cadastro e link para o login (auth 22)", async () => {
  renderRegister()
  expect(screen.getByRole("heading", { name: "Criar conta" })).toBeVisible()
  await userEvent.click(screen.getByRole("link", { name: "Entrar" }))
  expect(screen.getByRole("heading", { name: "Entrar" })).toBeVisible()
})

it("cadastro bem-sucedido leva à área autenticada (auth 23)", async () => {
  let sent: unknown
  server.use(
    http.post("/api/auth/register", async ({ request }) => {
      sent = await request.json()
      return HttpResponse.json(
        { id: "u1", email: "ana@x.com", username: "ana" },
        { status: 201 }
      )
    })
  )
  renderRegister()
  await fill("ana@x.com", "ana", "senha-forte-1")
  expect(await screen.findByRole("heading", { name: "Reuniões" })).toBeVisible()
  expect(sent).toEqual({
    email: "ana@x.com",
    username: "ana",
    password: "senha-forte-1",
  })
})

it("mostra erro de campo devolvido pela API (auth 25)", async () => {
  server.use(
    http.post("/api/auth/register", () =>
      HttpResponse.json(
        {
          error: {
            code: "validation_error",
            message: "Dados inválidos.",
            fields: { password: "senha com no máximo 72 bytes" },
          },
        },
        { status: 422 }
      )
    )
  )
  const { container } = renderRegister()
  await fill("ana@x.com", "ana", "é".repeat(37))
  expect(await screen.findByText("senha com no máximo 72 bytes")).toBeVisible()
  expect(screen.getByLabelText("Senha")).toHaveAttribute("aria-invalid", "true")
  expect(screen.getByLabelText("Senha")).toHaveAccessibleDescription(
    "senha com no máximo 72 bytes"
  )
  expect(await axe(container)).toHaveNoViolations()
})

it("mostra erro geral devolvido pela API (auth 25)", async () => {
  server.use(
    http.post("/api/auth/register", () =>
      HttpResponse.json(
        { error: { code: "internal_error", message: "erro interno" } },
        { status: 500 }
      )
    )
  )
  renderRegister()
  await fill("ana@x.com", "ana", "senha-forte-1")
  expect(await screen.findByRole("alert")).toHaveTextContent("erro interno")
  expect(screen.getByRole("heading", { name: "Criar conta" })).toBeVisible()
})

it("mostra o 409 sob o campo de email (auth 25)", async () => {
  server.use(
    http.post("/api/auth/register", () =>
      HttpResponse.json(
        {
          error: {
            code: "email_taken",
            message: "Este email já está cadastrado.",
            fields: { email: "Este email já está cadastrado." },
          },
        },
        { status: 409 }
      )
    )
  )
  renderRegister()
  await fill("ana@x.com", "ana", "senha-forte-1")
  expect(
    await screen.findByText("Este email já está cadastrado.")
  ).toBeVisible()
  expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true")
})

it("passa no axe sem erro", async () => {
  const { container } = renderRegister()
  expect(await axe(container)).toHaveNoViolations()
})
