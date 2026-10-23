// Orçamento de JS (ADR-0023; NFR-01 e NFR-02). Roda depois do `npm run build`.
// Inicial = chunk de entrada + imports estáticos (o que a rota de login baixa).
// Total = todo .js de dist/. Limites em KiB gzip; variáveis sobrescrevem para teste.
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"
import { gzipSync } from "node:zlib"

const dist = join(import.meta.dirname, "..", "dist")
const initialLimit = Number(process.env.BUNDLE_INITIAL_LIMIT_KB ?? 200)
const totalLimit = Number(process.env.BUNDLE_TOTAL_LIMIT_KB ?? 500)

const manifest = JSON.parse(
  readFileSync(join(dist, ".vite", "manifest.json"), "utf8")
)
const gzipKb = (file) => gzipSync(readFileSync(join(dist, file))).length / 1024

const initialFiles = new Set()
const visit = (key) => {
  const chunk = manifest[key]
  if (!chunk || initialFiles.has(chunk.file)) return
  initialFiles.add(chunk.file)
  for (const dep of chunk.imports ?? []) visit(dep)
}
for (const [key, chunk] of Object.entries(manifest)) {
  if (chunk.isEntry) visit(key)
}

const allJs = readdirSync(join(dist, "assets"))
  .filter((name) => name.endsWith(".js"))
  .map((name) => join("assets", name))

const sum = (files) => [...files].reduce((acc, file) => acc + gzipKb(file), 0)
const initial = sum(initialFiles)
const total = sum(allJs)

console.log(
  `JS inicial: ${initial.toFixed(1)} KiB gzip (limite ${initialLimit})`
)
console.log(`JS total:   ${total.toFixed(1)} KiB gzip (limite ${totalLimit})`)

if (initialFiles.size === 0) {
  console.error("manifesto sem chunk de entrada")
  process.exit(1)
}
if (initial > initialLimit || total > totalLimit) {
  console.error("orçamento de JS estourado (NFR-01, NFR-02)")
  process.exit(1)
}
