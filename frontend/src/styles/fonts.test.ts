import { existsSync, readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

// Fontes do Ata (ADR-0024, "Tipografia"): três famílias locais, preload de duas.
const read = (rel: string) =>
  readFileSync(resolve(import.meta.dirname, rel), "utf8")
const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "")
const tokensCss = stripComments(read("./tokens.css"))
const indexCss = stripComments(read("../index.css"))
const indexHtml = read("../../index.html")
const fontsDir = resolve(import.meta.dirname, "../../public/fonts")

function familyVar(name: string): string {
  const m = tokensCss.match(new RegExp(`${name}:\\s*([^;]+);`))
  if (!m) throw new Error(`${name} não achado`)
  return m[1].replace(/\s+/g, " ").trim()
}

describe("famílias", () => {
  it("cada --font-* do @theme aponta para a família certa", () => {
    expect(indexCss).toMatch(/--font-heading:\s*var\(--font-family-serif\)/)
    expect(indexCss).toMatch(/--font-serif:\s*var\(--font-family-serif\)/)
    expect(indexCss).toMatch(/--font-sans:\s*var\(--font-family-sans\)/)
    expect(indexCss).toMatch(/--font-mono:\s*var\(--font-family-mono\)/)
    expect(familyVar("--font-family-serif")).toMatch(
      /^"Source Serif 4 Variable"/
    )
    expect(familyVar("--font-family-sans")).toMatch(/^"Geist Variable"/)
    expect(familyVar("--font-family-mono")).toMatch(/^"Geist Mono Variable"/)
  })

  it("fallback com métricas ajustadas para serif e sans (NFR-05)", () => {
    for (const fam of ["Geist Fallback", "Source Serif 4 Fallback"]) {
      const face = tokensCss.match(
        new RegExp(`@font-face\\s*\\{[^}]*font-family:\\s*"${fam}"[^}]*\\}`)
      )
      expect(face, fam).not.toBeNull()
      for (const prop of [
        "size-adjust",
        "ascent-override",
        "descent-override",
        "line-gap-override",
      ]) {
        expect(face![0]).toContain(prop)
      }
    }
    expect(familyVar("--font-family-serif")).toContain(
      "Source Serif 4 Fallback"
    )
    expect(familyVar("--font-family-sans")).toContain("Geist Fallback")
  })

  it("toda fonte web usa font-display: swap", () => {
    const faces = [...tokensCss.matchAll(/@font-face\s*\{([^}]*)\}/g)]
      .map((m) => m[1])
      .filter((body) => body.includes("url("))
    expect(faces).toHaveLength(6)
    for (const body of faces) expect(body).toMatch(/font-display:\s*swap/)
  })
})

describe("arquivos e carga", () => {
  it("os quatro .woff2 novos e as licenças estão em public/fonts", () => {
    for (const f of [
      "source-serif-4-latin-wght-normal.woff2",
      "source-serif-4-latin-ext-wght-normal.woff2",
      "geist-mono-latin-wght-normal.woff2",
      "geist-mono-latin-ext-wght-normal.woff2",
      "LICENSE-SourceSerif4.txt",
      "LICENSE-GeistMono.txt",
      "LICENSE-Geist.txt",
    ]) {
      expect(existsSync(resolve(fontsDir, f)), f).toBe(true)
    }
  })

  it("preload só da Geist latin e da Source Serif 4 latin", () => {
    const preloads = [
      ...indexHtml.matchAll(/rel="preload"\s+href="([^"]+)"\s+as="font"/g),
    ].map((m) => m[1])
    expect(preloads.sort()).toEqual([
      "/fonts/geist-latin-wght-normal.woff2",
      "/fonts/source-serif-4-latin-wght-normal.woff2",
    ])
  })

  it("nenhuma URL http em tokens.css, index.css e index.html (SEC-13)", () => {
    for (const text of [tokensCss, indexCss, indexHtml]) {
      expect(text).not.toMatch(/https?:\/\//)
    }
  })
})
