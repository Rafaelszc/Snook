import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { afterEach, describe, expect, it } from "vitest"
import { axe } from "vitest-axe"

import { routes } from "./routes"
import { SamplePage } from "./SamplePage"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"

afterEach(() => localStorage.clear())

const render = (ui: React.ReactElement) => renderWithProviders(ui)

describe("SamplePage", () => {
  it("mostra tokens Ata e os componentes novos", () => {
    render(<SamplePage />)
    expect(
      screen.getByRole("heading", { level: 1, name: "Componentes" })
    ).toBeInTheDocument()
    for (const token of ["canvas", "ink", "signal", "failed-soft"]) {
      expect(screen.getByText(token)).toBeInTheDocument()
    }
    for (const v of ["primary", "accent", "secondary", "ghost", "danger"]) {
      expect(screen.getByRole("button", { name: v })).toBeInTheDocument()
    }
    expect(document.querySelectorAll('[data-slot="notice"]')).toHaveLength(4)
    const badges = screen.getByRole("list", { name: "Status" })
    expect(within(badges).getAllByRole("listitem")).toHaveLength(7)
    expect(document.querySelector('[data-slot="page-header"]')).not.toBeNull()
    expect(document.querySelector('[data-slot="skeleton"]')).not.toBeNull()
    expect(document.querySelector('[data-slot="empty-state"]')).not.toBeNull()
    expect(screen.getByRole("group", { name: "Tema" })).toBeInTheDocument()
  })

  it("um vidro só, como painel da gravação, sem gradiente", () => {
    render(<SamplePage />)
    expect(document.querySelectorAll("[data-slot=glass-panel]")).toHaveLength(1)
    const src = readFileSync(
      resolve(import.meta.dirname, "SamplePage.tsx"),
      "utf8"
    )
    expect(src).not.toMatch(/highlight|gradient/)
  })

  it.each(["light", "dark"])(
    "não tem violação de acessibilidade no tema %s",
    async (theme) => {
      localStorage.setItem("theme", theme)
      const { container } = render(<SamplePage />)
      expect(await axe(container)).toHaveNoViolations()
    }
  )

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
