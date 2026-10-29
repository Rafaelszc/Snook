import { existsSync, readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

import { contrast } from "@/test/color"

// O Vitest esvazia CSS importado (?raw incluído); lê do disco.
const read = (rel: string) =>
  readFileSync(resolve(import.meta.dirname, rel), "utf8")
const indexCss = read("../index.css")
const motionCss = read("./motion.css")
const tokensCss = read("./tokens.css")

function stripComments(css: string) {
  return css.replace(/\/\*[\s\S]*?\*\//g, "")
}

function vars(css: string, selector: string): Record<string, string> {
  const block = stripComments(css).match(
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

// Apelidos (var(--x)) resolvem no próprio tema.
function resolved(t: Record<string, string>): Record<string, string> {
  const get = (v: string, depth = 0): string => {
    const ref = v.match(/^var\((--[\w-]+)\)$/)
    if (!ref || depth > 8) return v
    return get(t[ref[1]] ?? v, depth + 1)
  }
  return Object.fromEntries(Object.entries(t).map(([k, v]) => [k, get(v)]))
}

const themes = {
  claro: resolved(vars(tokensCss, ":root")),
  escuro: resolved({
    ...vars(tokensCss, ":root"),
    ...vars(tokensCss, ".dark"),
  }),
}

// Texto normal: 4,5:1 (WCAG 1.4.3). Tabelas "Contraste" do ADR-0024.
const softs = ["--warn-soft", "--failed-soft", "--signal-soft"]
const textPairs: [string, string][] = [
  ...[
    "--ink",
    "--ink-muted",
    "--signal",
    "--done",
    "--warn",
    "--failed",
  ].flatMap((fg): [string, string][] => [
    [fg, "--canvas"],
    [fg, "--surface"],
    [fg, "--sunken"],
  ]),
  ["--signal-ink", "--signal"],
  ["--primary-foreground", "--primary"],
  ...["--ink", "--ink-muted"].flatMap((fg) =>
    softs.map((bg): [string, string] => [fg, bg])
  ),
  ["--warn", "--warn-soft"],
  ["--failed", "--failed-soft"],
  ["--signal", "--signal-soft"],
  ...["--done", "--warn", "--failed"].map((fg): [string, string] => [
    fg,
    "--signal-soft",
  ]),
  ["--foreground", "--background"],
  ["--card-foreground", "--card"],
  ["--popover-foreground", "--popover"],
  ["--primary-foreground", "--primary"],
  ["--secondary-foreground", "--secondary"],
  ["--muted-foreground", "--background"],
  ["--muted-foreground", "--muted"],
  ["--muted-foreground", "--card"],
  ["--accent-foreground", "--accent"],
  ["--highlight-foreground", "--highlight"],
  ["--highlight", "--background"],
  ["--highlight", "--card"],
  ["--destructive", "--background"],
  ["--destructive", "--card"],
  ["--sidebar-foreground", "--sidebar"],
  ["--status-pending", "--background"],
  ["--status-pending", "--card"],
  ["--status-processing", "--background"],
  ["--status-processing", "--card"],
  ["--status-done", "--background"],
  ["--status-done", "--card"],
  ["--status-failed", "--background"],
  ["--status-failed", "--card"],
]

// Componentes de UI (borda de campo, foco): 3:1 (WCAG 1.4.11).
const uiPairs: [string, string][] = [
  ["--input", "--canvas"],
  ["--input", "--surface"],
  ["--ring", "--canvas"],
  ["--ring", "--surface"],
  ["--input", "--background"],
  ["--input", "--card"],
  ["--ring", "--background"],
  ["--ring", "--card"],
]

describe.each(Object.entries(themes))("contraste, tema %s", (_name, t) => {
  it.each(textPairs)("%s sobre %s >= 4,5:1", (fg, bg) => {
    expect(contrast(t[fg], t[bg])).toBeGreaterThanOrEqual(4.5)
  })
  it.each(uiPairs)("%s sobre %s >= 3:1", (fg, bg) => {
    expect(contrast(t[fg], t[bg])).toBeGreaterThanOrEqual(3)
  })
})

describe("apelidos shadcn (ADR-0024)", () => {
  const aliases: Record<string, string> = {
    "--background": "--canvas",
    "--foreground": "--ink",
    "--card": "--surface",
    "--card-foreground": "--ink",
    "--popover": "--surface",
    "--popover-foreground": "--ink",
    "--primary": "--ink",
    "--primary-foreground": "--canvas",
    "--secondary": "--sunken",
    "--secondary-foreground": "--ink",
    "--muted": "--sunken",
    "--muted-foreground": "--ink-muted",
    "--accent": "--sunken",
    "--accent-foreground": "--ink",
    "--destructive": "--failed",
    "--border": "--hairline",
    "--ring": "--signal",
  }
  const raw = vars(tokensCss, ":root")

  it.each(Object.entries(aliases))("%s = var(%s)", (alias, token) => {
    expect(raw[alias]).toBe(`var(${token})`)
  })

  it("o @theme expõe as cores Ata", () => {
    const css = stripComments(indexCss)
    for (const name of [
      "canvas",
      "surface",
      "sunken",
      "hairline",
      "ink",
      "ink-muted",
      "signal",
      "signal-ink",
      "signal-soft",
      "done",
      "warn",
      "warn-soft",
      "failed",
      "failed-soft",
      "scrim",
    ]) {
      expect(css).toMatch(new RegExp(`--color-${name}:\\s*var\\(--${name}\\);`))
    }
  })
})

describe("tipografia", () => {
  it("escala 12, 14, 16, 20, 24, 32, 40 px", () => {
    const px = Object.entries(themes.claro)
      .filter(([k]) => k.startsWith("--fs-"))
      .map(([, v]) => parseFloat(v) * 16)
    expect(px).toEqual([12, 14, 16, 20, 24, 32, 40])
  })

  it("o Tailwind lê os tokens, não valores soltos", () => {
    const css = stripComments(indexCss)
    expect(css).toMatch(/--text-base:\s*var\(--fs-16\)/)
    expect(css).toMatch(/--font-sans:\s*var\(--font-family-sans\)/)
    expect(css).toMatch(/--color-background:\s*var\(--background\)/)
    expect(css).toMatch(/--color-highlight:\s*var\(--highlight\)/)
  })
})

describe("fonte local (SEC-13)", () => {
  it("sem URL externa nem @import remoto", () => {
    for (const css of [tokensCss, motionCss, indexCss]) {
      expect(css).not.toMatch(/https?:\/\//)
      expect(css).not.toMatch(/@import\s+url\(/)
    }
  })

  it("todo @font-face aponta para arquivo em public/fonts", () => {
    const urls = [...tokensCss.matchAll(/url\("(\/fonts\/[^"]+)"\)/g)].map(
      (m) => m[1]
    )
    expect(urls.length).toBeGreaterThan(0)
    for (const url of urls) {
      expect(
        existsSync(resolve(import.meta.dirname, "../../public", url.slice(1)))
      ).toBe(true)
    }
  })
})

describe("movimento", () => {
  const css = stripComments(motionCss)
  const allowed = new Set(["transform", "opacity"])

  it("tokens de duração ficam entre 120 e 240 ms", () => {
    for (const k of ["--motion-fast", "--motion-base", "--motion-slow"]) {
      const ms = parseFloat(themes.claro[k])
      expect(ms).toBeGreaterThanOrEqual(120)
      expect(ms).toBeLessThanOrEqual(240)
    }
  })

  it("transições animam só transform e opacity", () => {
    const decls = [...css.matchAll(/transition(?:-property)?\s*:\s*([^;]+);/g)]
    const props = decls
      .flatMap((m) => m[1].split(","))
      .map((part) => part.trim().split(/\s+/)[0])
      .filter((p) => p !== "none")
    expect(props.length).toBeGreaterThan(0)
    for (const p of props) expect(allowed.has(p)).toBe(true)
  })

  it("keyframes mexem só em transform e opacity", () => {
    const frames = [
      ...css.matchAll(/@keyframes[^{]+\{((?:[^{}]*\{[^}]*\})*)\s*\}/g),
    ]
    expect(frames.length).toBeGreaterThan(0)
    for (const [, body] of frames) {
      const props = [...body.matchAll(/([\w-]+)\s*:/g)].map((m) => m[1])
      for (const p of props) expect(allowed.has(p)).toBe(true)
    }
  })

  it("prefers-reduced-motion desliga cada classe de movimento", () => {
    const reduced = css.match(
      /@media \(prefers-reduced-motion: reduce\)\s*\{([\s\S]*)\}\s*$/
    )
    expect(reduced).not.toBeNull()
    const classes = [...css.matchAll(/^\.(motion-[\w-]+)\s*\{/gm)].map(
      (m) => m[1]
    )
    for (const c of classes) expect(reduced![1]).toContain(`.${c}`)
    expect(reduced![1]).toMatch(/transition:\s*none/)
    expect(reduced![1]).toMatch(/animation:\s*none/)
  })
})
