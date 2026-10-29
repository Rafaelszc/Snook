import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { axe } from "vitest-axe"

import { STATUS_LABELS } from "./messages"
import { StatusBadge, type Status } from "./StatusBadge"

const expected: Record<Status, string> = {
  pending: "Pendente",
  processing: "Processando",
  transcribed: "Transcrita",
  needs_split: "Precisa dividir",
  generating: "Gerando backlog",
  done: "Concluída",
  failed: "Falhou",
}

describe("StatusBadge", () => {
  it.each(Object.entries(expected))(
    "mostra texto pt-BR para %s",
    (status, label) => {
      render(<StatusBadge status={status as Status} />)
      expect(screen.getByText(label)).toBeInTheDocument()
      expect(STATUS_LABELS[status as Status]).toBe(label)
    }
  )

  // ADR-0024, "Estados": cores Ata.
  it.each([
    ["pending", "text-ink-muted"],
    ["processing", "text-signal"],
    ["transcribed", "text-ink"],
    ["needs_split", "text-warn"],
    ["generating", "text-signal"],
    ["done", "text-done"],
    ["failed", "text-failed"],
  ] as const)("%s: ícone em %s, sem pílula", (status, color) => {
    render(<StatusBadge status={status} />)
    const badge = screen.getByRole("status")
    expect(badge.querySelector("svg")).toHaveClass(color)
    expect(badge).toHaveClass(status === "failed" ? "text-failed" : "text-ink")
    expect(badge.className).not.toMatch(/\b(border|rounded|bg-)/)
  })

  it("cobre exatamente os 7 status", () => {
    expect(Object.keys(STATUS_LABELS).sort()).toEqual(
      Object.keys(expected).sort()
    )
  })

  it("não depende só de cor: cada status tem ícone próprio, oculto ao leitor de tela", () => {
    const icons = Object.keys(expected).map((status) => {
      const { container, unmount } = render(
        <StatusBadge status={status as Status} />
      )
      const svg = container.querySelector("svg")
      expect(svg).toHaveAttribute("aria-hidden", "true")
      const key = svg!.getAttribute("class")
      unmount()
      return key
    })
    expect(new Set(icons).size).toBe(Object.keys(expected).length)
  })

  it("anuncia mudança de status em região aria-live", () => {
    const { rerender } = render(<StatusBadge status="pending" />)
    const region = screen.getByRole("status")
    expect(region).toHaveAttribute("aria-live", "polite")
    expect(region).toHaveTextContent("Pendente")

    rerender(<StatusBadge status="processing" />)
    // Mesma região (é o que o leitor de tela observa), novo texto.
    expect(screen.getByRole("status")).toBe(region)
    expect(region).toHaveTextContent("Processando")
  })

  it("não tem violação de acessibilidade", async () => {
    const { container } = render(<StatusBadge status="failed" />)
    expect(await axe(container)).toHaveNoViolations()
  })
})
