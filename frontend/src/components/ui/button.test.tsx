import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { axe } from "vitest-axe"
import { describe, expect, it } from "vitest"

import { Button } from "./button"

// ADR-0024, "Componentes", "Foco" e "Movimento".
const classes = (el: HTMLElement) => el.className.split(/\s+/)

describe("Button", () => {
  it.each([
    ["primary", ["bg-primary", "text-primary-foreground"]],
    ["accent", ["bg-signal", "text-signal-ink"]],
    ["secondary", ["bg-transparent", "border-input", "hover:bg-sunken"]],
    ["ghost", ["hover:bg-sunken"]],
    ["danger", ["text-failed", "border-failed", "hover:bg-failed-soft"]],
  ] as const)("variante %s", (variant, expected) => {
    render(<Button variant={variant}>Ok</Button>)
    expect(classes(screen.getByRole("button"))).toEqual(
      expect.arrayContaining([...expected])
    )
  })

  it("sem variant explícita renderiza primary", () => {
    render(<Button>Ok</Button>)
    const button = screen.getByRole("button")
    expect(button).toHaveAttribute("data-variant", "primary")
    expect(classes(button)).toContain("bg-primary")
  })

  it("foco opaco de 2 px em --ring; hover sem transição de cor", () => {
    render(<Button>Ok</Button>)
    const c = classes(screen.getByRole("button"))
    expect(c).toEqual(
      expect.arrayContaining([
        "focus-visible:ring-2",
        "focus-visible:ring-ring",
        "focus-visible:ring-offset-2",
      ])
    )
    expect(c.filter((x) => /(ring|outline)-[\w-]+\/\d+/.test(x))).toEqual([])
    expect(c).not.toContain("transition-colors")
    expect(c).not.toContain("transition-all")
  })

  it.each([
    ["default", "h-9"],
    ["sm", "h-8"],
    ["icon", "size-9"],
    ["icon-sm", "size-8"],
  ] as const)("tamanho %s", (size, expected) => {
    render(
      <Button size={size} aria-label="Ok">
        Ok
      </Button>
    )
    expect(classes(screen.getByRole("button"))).toContain(expected)
  })

  it("raio --r-6 e espaço da escala", () => {
    render(<Button>Ok</Button>)
    const c = classes(screen.getByRole("button"))
    expect(c).toContain("rounded-md")
    const spacing = c.filter((x) => /^(p[xytrbl]?|gap|m[xytrbl]?)-/.test(x))
    for (const x of spacing) {
      expect(x).toMatch(/-(0|1|2|3|4|6|8|12|16)$/)
    }
  })

  it("opera por teclado", async () => {
    render(<Button>Ok</Button>)
    await userEvent.tab()
    expect(screen.getByRole("button")).toHaveFocus()
  })

  it("não tem violação de acessibilidade", async () => {
    const { container } = render(
      <div>
        {(["primary", "accent", "secondary", "ghost", "danger"] as const).map(
          (v) => (
            <Button key={v} variant={v}>
              {v}
            </Button>
          )
        )}
      </div>
    )
    expect(await axe(container)).toHaveNoViolations()
  })
})
