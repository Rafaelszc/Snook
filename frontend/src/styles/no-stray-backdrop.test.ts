import { readdirSync, readFileSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

// ADR-0022: backdrop-filter só em glass.css (via GlassPanel).
const srcDir = join(import.meta.dirname, "..")
const ALLOWED = "styles/glass.css"
// Só consulta CSS.supports("backdrop-filter"); não aplica o efeito.
const SUPPORT_CHECK = "components/surfaces/GlassPanel.tsx"
const PATTERN =
  /backdrop-(?:filter|blur|brightness|contrast|grayscale|hue-rotate|invert|opacity|saturate|sepia)/

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory()
      ? walk(join(dir, e.name))
      : /\.(css|tsx?)$/.test(e.name) && !/\.test\.tsx?$/.test(e.name)
        ? [join(dir, e.name)]
        : []
  )
}

describe("backdrop-filter fora de glass.css", () => {
  it("só glass.css usa backdrop-filter (nem classe Tailwind backdrop-*)", () => {
    const offenders = walk(srcDir)
      .map((f) => relative(srcDir, f))
      .filter((f) => f !== ALLOWED && f !== SUPPORT_CHECK)
      .filter((f) => PATTERN.test(readFileSync(join(srcDir, f), "utf8")))
    expect(offenders).toEqual([])
  })

  it("detecta o uso: glass.css existe e tem backdrop-filter", () => {
    expect(readFileSync(join(srcDir, ALLOWED), "utf8")).toMatch(
      /backdrop-filter/
    )
  })
})
