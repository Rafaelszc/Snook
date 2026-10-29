import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { act, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ThemeProvider, useTheme } from "./theme-provider"

function Probe() {
  const { theme, setTheme } = useTheme()
  return (
    <>
      <span data-testid="theme">{theme}</span>
      <button onClick={() => setTheme("dark")}>escuro</button>
    </>
  )
}

const renderProvider = () =>
  render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>
  )

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

describe("ThemeProvider", () => {
  it("não registra listener de keydown (WCAG 2.1.4)", () => {
    const add = vi.spyOn(window, "addEventListener")
    renderProvider()
    expect(add.mock.calls.map(([type]) => type)).not.toContain("keydown")
    add.mockRestore()
    const src = readFileSync(
      resolve(import.meta.dirname, "theme-provider.tsx"),
      "utf8"
    )
    expect(src).not.toMatch(/keydown/)
  })

  it("apertar d não muda o tema", async () => {
    renderProvider()
    await userEvent.keyboard("d")
    expect(screen.getByTestId("theme")).toHaveTextContent("system")
    expect(document.documentElement).toHaveClass("light")
  })

  it("grava a preferência em localStorage e a reaplica ao recarregar", async () => {
    const { unmount } = renderProvider()
    await userEvent.click(screen.getByRole("button", { name: "escuro" }))
    expect(localStorage.getItem("theme")).toBe("dark")
    unmount()
    renderProvider()
    expect(screen.getByTestId("theme")).toHaveTextContent("dark")
    expect(document.documentElement).toHaveClass("dark")
  })

  it("segue a troca feita em outra aba", () => {
    renderProvider()
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: "theme",
          newValue: "dark",
          storageArea: localStorage,
        })
      )
    })
    expect(screen.getByTestId("theme")).toHaveTextContent("dark")
  })

  it("só a chave de tema vai ao storage, nunca sessão", async () => {
    renderProvider()
    await userEvent.click(screen.getByRole("button", { name: "escuro" }))
    expect(Object.keys(localStorage)).toEqual(["theme"])
    expect(sessionStorage.length).toBe(0)
  })
})
