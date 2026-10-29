import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router"
import { axe } from "vitest-axe"
import { afterEach, describe, expect, it, vi } from "vitest"

import { renderWithProviders } from "@/test/render"

import { AppShell } from "./AppShell"

afterEach(() => localStorage.clear())

const LINKS = [
  { to: "/", label: "Reuniões" },
  { to: "/settings", label: "Configurações" },
]

function renderShell(path = "/", onLogout = vi.fn()) {
  const element = (
    <AppShell links={LINKS} userName="ana" onLogout={onLogout}>
      <p>conteúdo</p>
    </AppShell>
  )
  const router = createMemoryRouter(
    [
      { path: "/", element },
      { path: "/settings", element },
    ],
    { initialEntries: [path] }
  )
  return renderWithProviders(<RouterProvider router={router} />)
}

describe("AppShell", () => {
  it("marca o item ativo com aria-current e sublinhado em --signal", () => {
    renderShell("/settings")
    const nav = screen.getByRole("navigation", { name: "Principal" })
    const active = screen.getByRole("link", { name: "Configurações" })
    expect(nav).toContainElement(active)
    expect(active).toHaveAttribute("aria-current", "page")
    expect(active).toHaveClass("border-b-2", "border-signal")
    const other = screen.getByRole("link", { name: "Reuniões" })
    expect(other).not.toHaveAttribute("aria-current")
    expect(other).toHaveClass("border-transparent")
  })

  it("nav opera por teclado", async () => {
    renderShell("/")
    await userEvent.tab()
    expect(screen.getByRole("link", { name: "Snook, início" })).toHaveFocus()
    await userEvent.tab()
    expect(screen.getByRole("link", { name: "Reuniões" })).toHaveFocus()
    await userEvent.tab()
    await userEvent.keyboard("{Enter}")
    expect(
      await screen.findByRole("link", { name: "Configurações" })
    ).toHaveAttribute("aria-current", "page")
  })

  it("marca em serif, ThemeToggle, usuário e sair", async () => {
    const onLogout = vi.fn()
    renderShell("/", onLogout)
    expect(screen.getByRole("link", { name: "Snook, início" })).toHaveClass(
      "font-heading"
    )
    expect(screen.getByRole("group", { name: "Tema" })).toBeInTheDocument()
    expect(screen.getByText("ana")).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "Sair" }))
    expect(onLogout).toHaveBeenCalledOnce()
  })

  it("barra opaca e conteúdo em --shell", () => {
    renderShell()
    expect(screen.getByRole("main")).toHaveClass("max-w-shell")
    expect(screen.getByRole("main")).toHaveTextContent("conteúdo")
    expect(screen.getByRole("banner").className).not.toMatch(/glass|backdrop/)
    const src = readFileSync(
      resolve(import.meta.dirname, "AppShell.tsx"),
      "utf8"
    )
    expect(src).not.toMatch(/backdrop|GlassPanel|@\/features/)
  })

  it.each(["light", "dark"])(
    "não tem violação de acessibilidade no tema %s",
    async (theme) => {
      localStorage.setItem("theme", theme)
      const { container } = renderShell()
      expect(await axe(container)).toHaveNoViolations()
    }
  )
})
