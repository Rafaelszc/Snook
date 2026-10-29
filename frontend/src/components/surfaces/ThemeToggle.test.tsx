import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { axe } from "vitest-axe"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ThemeProvider } from "@/components/theme-provider"

import { ThemeToggle } from "./ThemeToggle"

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
  )
})
afterEach(() => vi.unstubAllGlobals())

const renderToggle = () =>
  render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>
  )

describe("ThemeToggle", () => {
  it("oferece claro, escuro e sistema, com o atual marcado", () => {
    renderToggle()
    const group = screen.getByRole("group", { name: "Tema" })
    expect(group).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Sistema" })).toHaveAttribute(
      "aria-pressed",
      "true"
    )
    expect(screen.getByRole("button", { name: "Claro" })).toHaveAttribute(
      "aria-pressed",
      "false"
    )
  })

  it("opera por teclado e grava em localStorage", async () => {
    renderToggle()
    await userEvent.tab()
    expect(screen.getByRole("button", { name: "Claro" })).toHaveFocus()
    await userEvent.tab()
    await userEvent.keyboard("{Enter}")
    expect(screen.getByRole("button", { name: "Escuro" })).toHaveAttribute(
      "aria-pressed",
      "true"
    )
    expect(localStorage.getItem("theme")).toBe("dark")
    expect(document.documentElement).toHaveClass("dark")
  })

  it("alvo de pelo menos 24 px (size-8)", () => {
    renderToggle()
    for (const b of screen.getAllByRole("button"))
      expect(b).toHaveClass("size-8")
  })

  it.each(["light", "dark"])(
    "não tem violação de acessibilidade no tema %s",
    async (theme) => {
      localStorage.setItem("theme", theme)
      const { container } = renderToggle()
      expect(await axe(container)).toHaveNoViolations()
    }
  )
})
