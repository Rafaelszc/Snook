import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { routes } from "./routes"
import { renderWithProviders } from "@/test/render"

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return renderWithProviders(<RouterProvider router={router} />)
}

it("navega entre rotas placeholder pelo layout", async () => {
  const { container } = renderAt("/")
  expect(screen.getByRole("heading", { name: "Reuniões" })).toBeInTheDocument()
  await userEvent.click(screen.getByRole("link", { name: "Configurações" }))
  expect(
    screen.getByRole("heading", { name: "Configurações" })
  ).toBeInTheDocument()
  expect(await axe(container)).toHaveNoViolations()
})

it("login e cadastro ficam fora do layout autenticado", () => {
  renderAt("/login")
  expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument()
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument()
})

it("rota desconhecida mostra não encontrada", () => {
  renderAt("/nada")
  expect(
    screen.getByRole("heading", { name: "Página não encontrada" })
  ).toBeInTheDocument()
})

it("o ConsentNotice ainda não existe (Task 22.1)", () => {
  renderAt("/")
  expect(screen.queryByTestId("consent-notice")).not.toBeInTheDocument()
})
