import { render, screen } from "@testing-library/react"
import { axe } from "vitest-axe"
import { describe, expect, it } from "vitest"

import { Button } from "@/components/ui/button"

import { EmptyState } from "./EmptyState"

describe("EmptyState", () => {
  it("mostra título, descrição e ação", () => {
    render(
      <EmptyState
        title="Nenhuma reunião"
        description="Envie uma gravação para começar."
        action={<Button>Enviar</Button>}
      />
    )
    expect(screen.getByText("Nenhuma reunião")).toBeInTheDocument()
    expect(
      screen.getByText("Envie uma gravação para começar.")
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Enviar" })).toBeInTheDocument()
  })

  it("sem ação, não renderiza botão", () => {
    render(<EmptyState title="Nada aqui" />)
    expect(screen.queryByRole("button")).toBeNull()
  })

  it("sem card, sem sombra e sem raio acima de 10 px", () => {
    const { container } = render(<EmptyState title="Nada aqui" />)
    const box = container.querySelector('[data-slot="empty-state"]')!
    expect(box.className).not.toMatch(/shadow|bg-card|bg-surface|rounded/)
  })

  it("não tem violação de acessibilidade", async () => {
    const { container } = render(
      <EmptyState
        title="Nenhuma reunião"
        description="Envie uma gravação."
        action={<Button>Enviar</Button>}
      />
    )
    expect(await axe(container)).toHaveNoViolations()
  })
})
