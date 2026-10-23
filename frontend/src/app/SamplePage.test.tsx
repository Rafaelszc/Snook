import { render, screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { describe, expect, it } from "vitest"
import { axe } from "vitest-axe"

import { routes } from "./routes"
import { SamplePage } from "./SamplePage"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

describe("SamplePage", () => {
  it("mostra tokens, GlassPanel e os 7 badges", () => {
    render(<SamplePage />)
    expect(
      screen.getByRole("heading", { level: 1, name: "Componentes" })
    ).toBeInTheDocument()
    const badges = screen.getByRole("list", { name: "Status" })
    expect(within(badges).getAllByRole("listitem")).toHaveLength(7)
    expect(document.querySelector("[data-slot=glass-panel]")).not.toBeNull()
  })

  it("no máximo 3 vidros por tela (ADR-0023)", () => {
    render(<SamplePage />)
    expect(
      document.querySelectorAll("[data-slot=glass-panel]").length
    ).toBeLessThanOrEqual(3)
  })

  it("não tem violação de acessibilidade", async () => {
    const { container } = render(<SamplePage />)
    expect(await axe(container)).toHaveNoViolations()
  })

  it("rota de amostra existe só em desenvolvimento", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ id: "u1", email: "ana@x.com", username: "ana" })
      )
    )
    const router = createMemoryRouter(routes, {
      initialEntries: ["/dev/components"],
    })
    renderWithProviders(<RouterProvider router={router} />)
    // Vitest roda com import.meta.env.DEV verdadeiro.
    expect(
      await screen.findByRole("heading", { level: 1, name: "Componentes" })
    ).toBeInTheDocument()
  })
})
