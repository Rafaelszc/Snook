import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

// ADR-0024, "Classes de cor a trocar": tokens removidos não voltam.
const srcDir = join(import.meta.dirname, "..")
const SELF = "styles/removed-tokens.test.ts"
const SCOPE = ["components", "styles", "index.css", "app/SamplePage.tsx"]
const REMOVED =
  /highlight|status-(?:pending|processing|done|failed)|sidebar|chart-/
const REMOVED_CLASSES =
  /\b(?:text|bg|border)-highlight(?:-foreground)?\b|\btext-status-[\w-]+/
const REMOVED_VARS = /--(?:elevation-\d|radius)\s*:/

function walk(path: string): string[] {
  if (statSync(path).isFile()) return [path]
  return readdirSync(path, { withFileTypes: true }).flatMap((e) =>
    walk(join(path, e.name))
  )
}

const files = (roots: string[]) =>
  roots
    .flatMap((r) => walk(join(srcDir, r)))
    .filter((f) => /\.(css|tsx?)$/.test(f))
    .map((f) => ({ path: relative(srcDir, f), text: readFileSync(f, "utf8") }))
    .filter((f) => f.path !== SELF)

describe("tokens removidos", () => {
  it("components/, styles/, index.css e SamplePage sem nome antigo", () => {
    const hits = files(SCOPE)
      .filter((f) => REMOVED.test(f.text))
      .map((f) => f.path)
    expect(hits).toEqual([])
  })

  it("nenhuma classe de cor antiga em src/", () => {
    const hits = files(["."])
      .filter((f) => REMOVED_CLASSES.test(f.text))
      .map((f) => f.path)
    expect(hits).toEqual([])
  })

  it("tokens.css sem --elevation-* nem --radius", () => {
    const tokens = readFileSync(join(srcDir, "styles/tokens.css"), "utf8")
    expect(tokens).not.toMatch(REMOVED_VARS)
  })

  it("spotlight.css lê --signal", () => {
    const css = readFileSync(join(srcDir, "styles/spotlight.css"), "utf8")
    expect(css).toMatch(/var\(--signal\)/)
  })

  it("detecta o uso: o padrão acha nome antigo", () => {
    expect(REMOVED.test("var(--highlight)")).toBe(true)
    expect(REMOVED_CLASSES.test('className="text-status-done"')).toBe(true)
  })
})
