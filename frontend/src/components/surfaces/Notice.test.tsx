import { render, screen } from "@testing-library/react"
import { axe } from "vitest-axe"
import { describe, expect, it } from "vitest"

import { Notice, type NoticeVariant } from "./Notice"

const VARIANTS: [NoticeVariant, string, string][] = [
  ["info", "bg-signal-soft", "border-signal"],
  ["warn", "bg-warn-soft", "border-warn"],
  ["error", "bg-failed-soft", "border-failed"],
  ["consent", "bg-sunken", "border-ink-muted"],
]

describe("Notice", () => {
  it.each(VARIANTS)(
    "%s: fundo %s e régua esquerda de 2 px em %s",
    (variant, bg, rule) => {
      const { container } = render(<Notice variant={variant}>texto</Notice>)
      const box = container.querySelector('[data-slot="notice"]')
      expect(box).toHaveClass(bg, rule, "border-l-2", "text-ink")
      expect(box?.querySelector("svg")).toHaveAttribute("aria-hidden", "true")
    }
  )

  it("error é alert; info e warn são status; consent sem região viva", () => {
    const { rerender, container } = render(<Notice variant="error">x</Notice>)
    expect(screen.getByRole("alert")).toHaveTextContent("x")
    for (const v of ["info", "warn"] as const) {
      rerender(<Notice variant={v}>x</Notice>)
      expect(screen.getByRole("status")).toHaveTextContent("x")
    }
    rerender(<Notice variant="consent">x</Notice>)
    const box = container.querySelector('[data-slot="notice"]')
    expect(box).not.toHaveAttribute("role")
    expect(box).not.toHaveAttribute("aria-live")
  })

  it("role explícito troca a região viva da variante", () => {
    render(
      <Notice variant="warn" role="alert">
        x
      </Notice>
    )
    const box = screen.getByRole("alert")
    expect(box).toHaveAttribute("data-variant", "warn")
  })

  it("mensagem é só texto, mesmo com <script> (SEC-12)", () => {
    const evil = '<script>alert(1)</script><img src=x onerror="alert(2)">'
    const { container } = render(<Notice variant="error">{evil}</Notice>)
    expect(screen.getByRole("alert")).toHaveTextContent(evil)
    expect(container.querySelector("script, img")).toBeNull()
  })

  it.each(VARIANTS.map(([v]) => v))(
    "%s não tem violação de acessibilidade",
    async (variant) => {
      const { container } = render(
        <Notice variant={variant}>Aviso de teste</Notice>
      )
      expect(await axe(container)).toHaveNoViolations()
    }
  )
})
