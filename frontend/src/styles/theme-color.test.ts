import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

import { parseColor, toHex } from "@/test/color"

// ADR-0024, "Tema": theme-color acompanha --canvas de cada tema.
const read = (rel: string) =>
  readFileSync(resolve(import.meta.dirname, rel), "utf8")
const tokensCss = read("./tokens.css").replace(/\/\*[\s\S]*?\*\//g, "")
const indexHtml = read("../../index.html")

function canvas(selector: string): string {
  const block = tokensCss.match(
    new RegExp(`(?:^|\\})\\s*${selector.replace(".", "\\.")}\\s*\\{([^}]*)\\}`)
  )
  return block![1].match(/--canvas:\s*([^;]+);/)![1].trim()
}

function meta(scheme: "light" | "dark"): string {
  const m = indexHtml.match(
    new RegExp(
      `<meta\\s+name="theme-color"\\s+content="(#[0-9a-f]{6})"\\s+media="\\(prefers-color-scheme: ${scheme}\\)"`,
      "i"
    )
  )
  if (!m) throw new Error(`theme-color ${scheme} não achado`)
  return m[1]
}

const channels = (hex: string) =>
  [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))

describe("theme-color", () => {
  it.each([
    ["light", ":root"],
    ["dark", ".dark"],
  ] as const)(
    "%s igual a --canvas, com tolerância de 1 por canal",
    (scheme, sel) => {
      const expected = channels(toHex(parseColor(canvas(sel))))
      const actual = channels(meta(scheme))
      actual.forEach((c, i) =>
        expect(Math.abs(c - expected[i])).toBeLessThanOrEqual(1)
      )
    }
  )

  it("o preload de fontes segue intacto", () => {
    expect(indexHtml).toContain('href="/fonts/geist-latin-wght-normal.woff2"')
    expect(indexHtml).toContain(
      'href="/fonts/source-serif-4-latin-wght-normal.woff2"'
    )
  })
})
