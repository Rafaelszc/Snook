import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { render, screen } from "@testing-library/react"
import { axe } from "vitest-axe"
import { describe, expect, it } from "vitest"

import { Button } from "@/components/ui/button"

import { PageHeader } from "./PageHeader"

describe("PageHeader", () => {
  it("h1 serif, descrição em --ink-muted e ações", () => {
    render(
      <PageHeader
        title="Reuniões"
        description="Suas gravações"
        actions={<Button>Nova</Button>}
      />
    )
    const h1 = screen.getByRole("heading", { level: 1, name: "Reuniões" })
    expect(h1).toHaveClass("font-heading")
    expect(screen.getByText("Suas gravações")).toHaveClass("text-ink-muted")
    expect(screen.getByRole("button", { name: "Nova" })).toBeInTheDocument()
  })

  it("sem descrição nem ações, só o título", () => {
    const { container } = render(<PageHeader title="Ajustes" />)
    expect(container.querySelectorAll("p, button")).toHaveLength(0)
  })

  it("só tamanhos e espaço da escala, sem text-[", () => {
    const src = readFileSync(
      resolve(import.meta.dirname, "PageHeader.tsx"),
      "utf8"
    )
    expect(src).not.toMatch(/text-\[/)
    for (const [, n] of src.matchAll(
      /\b(?:gap|p[xytrbl]?|m[xytrbl]?)-(\d+)/g
    )) {
      expect(["1", "2", "3", "4", "6", "8", "12", "16"]).toContain(n)
    }
  })

  it("não tem violação de acessibilidade", async () => {
    const { container } = render(
      <PageHeader
        title="Reuniões"
        description="Suas gravações"
        actions={<Button>Nova</Button>}
      />
    )
    expect(await axe(container)).toHaveNoViolations()
  })
})
