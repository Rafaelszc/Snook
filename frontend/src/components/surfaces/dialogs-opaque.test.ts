import { readdirSync, readFileSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

// ADR-0024, "Vidro": todo diálogo é opaco, sobre DialogSurface, sem GlassPanel.
const srcDir = join(import.meta.dirname, "..", "..")
const DIALOG_IMPORT =
  /import\s*\{[^}]*\b(?:AlertDialog|Dialog)\b[^}]*\}\s*from\s*"radix-ui"/
const SURFACE_IMPORT = /import\s*\{[^}]*\bDialogSurface\b[^}]*\}\s*from/
const GLASS_IMPORT = /import\s*\{[^}]*\bGlassPanel\b[^}]*\}\s*from/

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory()
      ? walk(join(dir, e.name))
      : /\.tsx$/.test(e.name) && !/\.test\.tsx$/.test(e.name)
        ? [join(dir, e.name)]
        : []
  )
}

function dialogFiles(dir = srcDir) {
  return walk(dir)
    .map((f) => ({ path: relative(srcDir, f), text: readFileSync(f, "utf8") }))
    .filter((f) => DIALOG_IMPORT.test(f.text))
}

function offenders(files: { path: string; text: string }[]) {
  return files
    .filter((f) => GLASS_IMPORT.test(f.text) || !SURFACE_IMPORT.test(f.text))
    .map((f) => f.path)
}

describe("diálogos opacos", () => {
  it("todo diálogo importa DialogSurface e não importa GlassPanel", () => {
    expect(offenders(dialogFiles())).toEqual([])
  })

  it("acha os 5 diálogos diretos", () => {
    expect(
      dialogFiles()
        .map((f) => f.path)
        .sort()
    ).toEqual([
      "components/surfaces/ConfirmDialog.tsx",
      "features/backlog-review/FormDialog.tsx",
      "features/backlog-review/RegenerateDialog.tsx",
      "features/llm-providers/RemoveDialog.tsx",
      "features/screen-recording/SourceWarningDialog.tsx",
    ])
  })

  it("acusa diálogo com GlassPanel ou sem DialogSurface", () => {
    const dialog = 'import { AlertDialog } from "radix-ui"\n'
    expect(
      offenders([
        {
          path: "vidro.tsx",
          text:
            dialog +
            'import { DialogSurface } from "./DialogSurface"\n' +
            'import { GlassPanel } from "./GlassPanel"\n',
        },
        { path: "sem-superficie.tsx", text: dialog },
        {
          path: "ok.tsx",
          text: dialog + 'import { DialogSurface } from "./DialogSurface"\n',
        },
      ])
    ).toEqual(["vidro.tsx", "sem-superficie.tsx"])
  })
})
