import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { render, screen } from "@testing-library/react"
import { axe } from "vitest-axe"
import { afterEach, describe, expect, it, vi } from "vitest"

import { contrast, parseColor, toHex } from "@/test/color"

import { GlassPanel } from "./GlassPanel"

const read = (rel: string) =>
  readFileSync(resolve(import.meta.dirname, rel), "utf8")
const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "")
const glassCss = stripComments(read("../../styles/glass.css"))
const tokensCss = stripComments(read("../../styles/tokens.css"))

function stubSupports(result: boolean) {
  vi.stubGlobal("CSS", { supports: vi.fn(() => result) })
}

afterEach(() => vi.unstubAllGlobals())

describe("GlassPanel", () => {
  it("com suporte a backdrop-filter, não força o fundo opaco", () => {
    stubSupports(true)
    render(<GlassPanel>conteúdo</GlassPanel>)
    const panel = screen.getByText("conteúdo")
    expect(panel).toHaveClass("glass")
    expect(panel).not.toHaveClass("glass-opaque")
  })

  it("sem suporte a backdrop-filter, usa a classe opaca", () => {
    stubSupports(false)
    render(<GlassPanel>conteúdo</GlassPanel>)
    expect(CSS.supports).toHaveBeenCalledWith("backdrop-filter", "blur(1px)")
    expect(screen.getByText("conteúdo")).toHaveClass("glass", "glass-opaque")
  })

  it("repassa className e atributos", () => {
    stubSupports(true)
    render(
      <GlassPanel className="p-4" role="dialog" aria-label="Aviso">
        x
      </GlassPanel>
    )
    const panel = screen.getByRole("dialog", { name: "Aviso" })
    expect(panel).toHaveClass("glass", "p-4")
  })

  it("não tem violação de acessibilidade", async () => {
    stubSupports(true)
    const { container } = render(
      <GlassPanel role="region" aria-label="Painel">
        <p>texto</p>
      </GlassPanel>
    )
    expect(await axe(container)).toHaveNoViolations()
  })
})

describe("glass.css: fallback opaco", () => {
  it("o estado base é opaco; o vidro só entra em @supports e sem preferências contrárias", () => {
    const base = glassCss.match(/(?:^|\})\s*\.glass\s*\{([^}]*)\}/)
    expect(base).not.toBeNull()
    expect(base![1]).not.toMatch(/backdrop-filter/)
    expect(base![1]).toMatch(/background:\s*var\(--card\)/)

    const enhanced = glassCss.match(
      /@supports \(backdrop-filter:\s*blur\(1px\)\)\s*\{([\s\S]*)\}\s*$/
    )
    expect(enhanced).not.toBeNull()
    expect(enhanced![1]).toMatch(
      /prefers-reduced-transparency:\s*no-preference/
    )
    expect(enhanced![1]).toMatch(/forced-colors:\s*none/)
    expect(enhanced![1]).toMatch(/\.glass:not\(\.glass-opaque\)/)
    expect(enhanced![1]).toMatch(
      /backdrop-filter:\s*blur\(12px\) saturate\(140%\)/
    )
  })

  it("forced-colors usa cores do sistema", () => {
    const forced = glassCss.match(
      /@media \(forced-colors: active\)\s*\{([\s\S]*?)\n\}/
    )
    expect(forced).not.toBeNull()
    expect(forced![1]).toMatch(/Canvas/)
    expect(forced![1]).toMatch(/CanvasText/)
  })
})

// Navegador compõe em sRGB (com gamma), não em linear.
function srgb(color: string): number[] {
  const hex = toHex(parseColor(color))
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
}

function over(fg: string, bg: string, alpha: number): string {
  const f = srgb(fg)
  const b = srgb(bg)
  return (
    "#" +
    f
      .map((c, i) =>
        Math.round(c * alpha + b[i] * (1 - alpha))
          .toString(16)
          .padStart(2, "0")
      )
      .join("")
  )
}

function vars(css: string, selector: string): Record<string, string> {
  const block = css.match(
    new RegExp(`(?:^|\\})\\s*${selector.replace(".", "\\.")}\\s*\\{([^}]*)\\}`)
  )
  if (!block) throw new Error(`bloco ${selector} não achado`)
  return Object.fromEntries(
    [...block[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => [
      m[1],
      m[2].trim(),
    ])
  )
}

describe("glass.css: contraste sobre o pior fundo", () => {
  const alpha =
    parseFloat(glassCss.match(/--glass-alpha:\s*([\d.]+)%/)![1]) / 100
  const light = vars(tokensCss, ":root")
  const dark = { ...light, ...vars(tokensCss, ".dark") }
  // Pior fundo: o extremo que mais aproxima o vidro da cor do texto.
  const worstBackdrops = ["#000000", "#ffffff"]

  describe.each([
    ["claro", light],
    ["escuro", dark],
  ])("tema %s", (_name, t) => {
    it.each(worstBackdrops)(
      "texto sobre vidro com fundo %s >= 4,5:1",
      (backdrop) => {
        const glass = over(t["--card"], backdrop, alpha)
        expect(contrast(t["--card-foreground"], glass)).toBeGreaterThanOrEqual(
          4.5
        )
        expect(contrast(t["--highlight"], glass)).toBeGreaterThanOrEqual(4.5)
      }
    )
  })
})
