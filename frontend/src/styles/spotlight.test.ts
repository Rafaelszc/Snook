import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

// Realce do upload (ADR-0024, "Mouse-tracking").
const raw = readFileSync(
  resolve(import.meta.dirname, "./spotlight.css"),
  "utf8"
)
const css = raw.replace(/\/\*[\s\S]*?\*\//g, "")
const comments = raw.match(/\/\*[\s\S]*?\*\//g)?.join("\n") ?? ""

describe("spotlight.css", () => {
  it("recorta o realce à faixa da borda por mask-composite", () => {
    expect(css).toMatch(/mask:[\s\S]*content-box exclude/)
    expect(css).toMatch(/-webkit-mask-composite:\s*xor/)
    expect(css).toMatch(/padding:\s*2px/)
  })

  // Ausência do token antigo: removed-tokens.test.ts varre styles/.
  it("pinta em --signal", () => {
    expect(css).toMatch(/radial-gradient\([^;]*var\(--signal\)/)
  })

  it("só liga com suporte a mask-composite, hover fino e sem movimento reduzido", () => {
    const base = css.slice(0, css.indexOf("@supports"))
    expect(base).toMatch(/\.spotlight::before\s*{\s*display:\s*none;/)
    expect(css).toMatch(
      /@supports \(mask-composite: exclude\) or \(-webkit-mask-composite: xor\)\s*{\s*@media \(hover: hover\) and \(pointer: fine\) and \(prefers-reduced-motion: no-preference\)/
    )
  })

  it("desliga em forced-colors", () => {
    expect(css).toMatch(
      /@media \(forced-colors: active\)\s*{\s*\.spotlight::before\s*{\s*display:\s*none;/
    )
  })

  it("o miolo não muda: nada além do ::before é pintado", () => {
    expect(css).not.toMatch(/\.spotlight(:hover)?\s*{[^}]*(background|color):/)
  })

  it("só anima opacity", () => {
    for (const [, value] of css.matchAll(/transition:\s*([^;]+);/g))
      expect(value).toMatch(/^opacity\b/)
  })

  it("comentário não cita login", () => {
    expect(comments).not.toMatch(/login/i)
  })
})
