import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { axe } from "vitest-axe"
import { describe, expect, it, vi } from "vitest"

import { Button } from "@/components/ui/button"

import { ConfirmDialog } from "./ConfirmDialog"
import { DialogSurface } from "./DialogSurface"

describe("DialogSurface", () => {
  it("é opaca: --surface, raio --r-10 e --overlay-shadow, sem vidro", () => {
    render(<DialogSurface>conteúdo</DialogSurface>)
    const surface = screen.getByText("conteúdo")
    expect(surface).toHaveAttribute("data-slot", "dialog-surface")
    expect(surface).toHaveClass("bg-surface", "rounded-lg", "shadow-overlay")
    expect(surface.className).not.toMatch(/glass|backdrop/)
  })

  it("o arquivo não usa backdrop-filter", () => {
    const src = readFileSync(
      resolve(import.meta.dirname, "DialogSurface.tsx"),
      "utf8"
    ).replace(/\/\/.*$/gm, "")
    expect(src).not.toMatch(/backdrop|GlassPanel/)
  })
})

describe("ConfirmDialog sobre DialogSurface", () => {
  function setup() {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        trigger={<Button>Excluir</Button>}
        title="Excluir reunião?"
        description="Não dá para desfazer."
        confirm="Excluir"
        destructive
        onConfirm={onConfirm}
      />
    )
    return onConfirm
  }

  it("abre opaco sobre --scrim e devolve o foco ao gatilho", async () => {
    setup()
    const trigger = screen.getByRole("button", { name: "Excluir" })
    await userEvent.click(trigger)
    const dialog = screen.getByRole("alertdialog")
    expect(dialog).toHaveAttribute("data-slot", "dialog-surface")
    expect(document.querySelector('[data-slot="glass-panel"]')).toBeNull()
    expect(document.querySelector(".bg-scrim")).not.toBeNull()
    expect(dialog).toContainElement(document.activeElement as HTMLElement)
    await userEvent.keyboard("{Escape}")
    expect(trigger).toHaveFocus()
  })

  it("não tem violação de acessibilidade", async () => {
    setup()
    await userEvent.click(screen.getByRole("button", { name: "Excluir" }))
    expect(await axe(document.body)).toHaveNoViolations()
  })
})
