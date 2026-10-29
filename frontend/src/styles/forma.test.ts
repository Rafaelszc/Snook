import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

// Forma do Ata (ADR-0024, "Forma" e "Profundidade").
const read = (rel: string) =>
  readFileSync(resolve(import.meta.dirname, rel), "utf8")
const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "")
const tokensCss = stripComments(read("./tokens.css"))
const indexCss = stripComments(read("../index.css"))

const token = (name: string) =>
  tokensCss.match(new RegExp(`${name}:\\s*([^;]+);`))?.[1].trim()

describe("raio", () => {
  it("--r-4, --r-6 e --r-10 valem 4, 6 e 10 px", () => {
    expect(token("--r-4")).toBe("0.25rem")
    expect(token("--r-6")).toBe("0.375rem")
    expect(token("--r-10")).toBe("0.625rem")
  })

  it("rounded-sm, -md e -lg leem --r-4, --r-6 e --r-10", () => {
    expect(indexCss).toMatch(/--radius-\*:\s*initial/)
    expect(indexCss).toMatch(/--radius-sm:\s*var\(--r-4\)/)
    expect(indexCss).toMatch(/--radius-md:\s*var\(--r-6\)/)
    expect(indexCss).toMatch(/--radius-lg:\s*var\(--r-10\)/)
  })

  it("não existe --radius-xl a --radius-4xl", () => {
    expect(indexCss).not.toMatch(/--radius-(xl|2xl|3xl|4xl)\s*:/)
  })
})

describe("sombra", () => {
  it("só --shadow-overlay no @theme", () => {
    expect(indexCss).toMatch(/--shadow-\*:\s*initial/)
    const shadows = [...indexCss.matchAll(/(--shadow-[\w-]+)\s*:/g)].map(
      (m) => m[1]
    )
    expect(shadows).toEqual(["--shadow-overlay"])
    expect(indexCss).toMatch(/--shadow-overlay:\s*var\(--overlay-shadow\)/)
  })
})

describe("larguras", () => {
  it("--shell 72rem e --reading 44rem, com utilitário max-w-*", () => {
    expect(token("--shell")).toBe("72rem")
    expect(token("--reading")).toBe("44rem")
    expect(indexCss).toMatch(/--container-shell:\s*var\(--shell\)/)
    expect(indexCss).toMatch(/--container-reading:\s*var\(--reading\)/)
  })
})
