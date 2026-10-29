import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { axe } from "vitest-axe"
import { describe, expect, it } from "vitest"

import { Input } from "./input"

// ADR-0024, "Forma" e "Foco": 40 px, --r-6, borda --input, anel opaco.
const classes = (el: HTMLElement) => el.className.split(/\s+/)

describe("Input", () => {
  it("tem 40 px, raio --r-6 e borda --input", () => {
    render(<Input aria-label="Nome" />)
    const c = classes(screen.getByRole("textbox", { name: "Nome" }))
    expect(c).toEqual(
      expect.arrayContaining(["h-10", "rounded-md", "border", "border-input"])
    )
  })

  it("foco: anel de 2 px em --ring, sem alfa, com afastamento", () => {
    render(<Input aria-label="Nome" />)
    const c = classes(screen.getByRole("textbox", { name: "Nome" }))
    expect(c).toEqual(
      expect.arrayContaining([
        "focus-visible:ring-2",
        "focus-visible:ring-ring",
        "focus-visible:ring-offset-2",
      ])
    )
    expect(c.filter((x) => /(ring|outline)-[\w-]+\/\d+/.test(x))).toEqual([])
  })

  it("inválido: borda --failed opaca", () => {
    render(<Input aria-label="Nome" aria-invalid />)
    const c = classes(screen.getByRole("textbox", { name: "Nome" }))
    expect(c).toContain("aria-invalid:border-failed")
    expect(c.filter((x) => x.startsWith("aria-invalid:ring"))).toEqual([])
  })

  it("recebe foco por teclado", async () => {
    render(<Input aria-label="Nome" />)
    await userEvent.tab()
    expect(screen.getByRole("textbox", { name: "Nome" })).toHaveFocus()
  })

  it("não tem violação de acessibilidade", async () => {
    const { container } = render(
      <label>
        Nome
        <Input />
      </label>
    )
    expect(await axe(container)).toHaveNoViolations()
  })

  it("index.css: contorno base sem alfa", () => {
    const css = readFileSync(
      resolve(import.meta.dirname, "../../index.css"),
      "utf8"
    )
    expect(css).not.toMatch(/(ring|outline)-ring\/\d+/)
    expect(css).toMatch(/outline-ring;/)
  })
})
