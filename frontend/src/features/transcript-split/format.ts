// Instante em hh:mm:ss, para fonte mono tabular.
export function formatTimestamp(seconds: number): string {
  const total = Math.floor(seconds)
  const h = String(Math.floor(total / 3600)).padStart(2, "0")
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, "0")
  const s = String(total % 60).padStart(2, "0")
  return `${h}:${m}:${s}`
}

const TOKENS = new Intl.NumberFormat("pt-BR")

export const formatTokens = (tokens: number) => TOKENS.format(tokens)
