import { readdirSync, readFileSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

// ADR-0024, "Testes novos": teste estático global do Ata em src/ (Task 61.4).
const srcDir = join(import.meta.dirname, "..")

const FORBIDDEN: [string, RegExp][] = [
  ["rounded-xl ou acima", /\brounded-(?:[a-z]{1,2}-)?(?:xl|[2-4]xl)\b/],
  ["text-[", /\btext-\[/],
  ["transition-colors", /\btransition-colors\b/],
  ["transition: all", /transition:\s*all\b/],
  ["ring-ring/50", /\bring-ring\/50\b/],
  ["outline-ring/50", /\boutline-ring\/50\b/],
]

// Onde `<GlassPanel` pode aparecer: o painel da gravação e a amostra de tokens.
const GLASS_ALLOWED = [
  "features/screen-recording/RecordingPanel.tsx",
  "app/SamplePage.tsx",
]

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory()
      ? walk(join(dir, e.name))
      : /\.(css|tsx?)$/.test(e.name) && !/\.test\.tsx?$/.test(e.name)
        ? [join(dir, e.name)]
        : []
  )
}

function sources(): [string, string][] {
  return walk(srcDir).map((f) => [relative(srcDir, f), readFileSync(f, "utf8")])
}

function violations(text: string): string[] {
  return FORBIDDEN.filter(([, re]) => re.test(text)).map(([name]) => name)
}

const glassUses = (text: string) => text.match(/<GlassPanel\b/g)?.length ?? 0

describe("teste estático do Ata", () => {
  it.each([
    ['className="rounded-xl"', "rounded-xl ou acima"],
    ['className="rounded-2xl"', "rounded-xl ou acima"],
    ['className="rounded-t-3xl"', "rounded-xl ou acima"],
    ['className="text-[13px]"', "text-["],
    ['className="transition-colors"', "transition-colors"],
    [".a { transition: all 200ms; }", "transition: all"],
    ['className="ring-ring/50"', "ring-ring/50"],
    ['className="outline-ring/50"', "outline-ring/50"],
  ])("acusa %s", (sample, name) => {
    expect(violations(sample)).toEqual([name])
  })

  it("aceita raio e transição do Ata", () => {
    expect(
      violations('className="rounded-lg rounded-md motion-press ring-ring"')
    ).toEqual([])
  })

  it("src/ sem padrão proibido", () => {
    const offenders = sources()
      .map(([file, text]) => [file, violations(text)] as const)
      .filter(([, found]) => found.length > 0)
    expect(offenders).toEqual([])
  })

  it("GlassPanel só no painel da gravação e na amostra, um por tela", () => {
    const uses = sources()
      .map(([file, text]) => [file, glassUses(text)] as const)
      .filter(([, n]) => n > 0)
    expect(uses.map(([file]) => file).sort()).toEqual([...GLASS_ALLOWED].sort())
    for (const [, n] of uses) expect(n).toBe(1)
  })

  it("conta usos de GlassPanel", () => {
    expect(glassUses("<GlassPanel a /><GlassPanel b>")).toBe(2)
    expect(glassUses('import { GlassPanel } from "x"')).toBe(0)
  })
})
