// Contraste WCAG 2.x a partir de cores CSS (oklch, hex). Só para testes.
export type Rgb = [number, number, number]

function linearToSrgb(c: number): number {
  const v = Math.min(1, Math.max(0, c))
  return v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055
}

function srgbToLinear(c: number): number {
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

// Oklab -> sRGB (Björn Ottosson). Retorna canais lineares 0..1.
function oklchToLinear(l: number, c: number, hDeg: number): Rgb {
  const h = (hDeg * Math.PI) / 180
  const a = c * Math.cos(h)
  const b = c * Math.sin(h)
  const l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3
  const m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3
  const s_ = (l - 0.0894841775 * a - 1.291485548 * b) ** 3
  return [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_,
  ]
}

export function parseColor(value: string): Rgb {
  const v = value.trim()
  const oklch = v.match(/^oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)$/)
  if (oklch) {
    const [l, c, h] = oklch.slice(1).map(Number)
    return oklchToLinear(l, c, h).map((x) => Math.min(1, Math.max(0, x))) as Rgb
  }
  const hex = v.match(/^#([0-9a-f]{6})$/i)
  if (hex) {
    const n = parseInt(hex[1], 16)
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((x) =>
      srgbToLinear(x / 255)
    ) as Rgb
  }
  throw new Error(
    `cor não suportada no teste (use oklch opaco ou #rrggbb): ${value}`
  )
}

export function luminance([r, g, b]: Rgb): number {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function contrast(fg: string, bg: string): number {
  const l1 = luminance(parseColor(fg))
  const l2 = luminance(parseColor(bg))
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1]
  return (hi + 0.05) / (lo + 0.05)
}

export function toHex(rgb: Rgb): string {
  return (
    "#" +
    rgb
      .map((x) =>
        Math.round(linearToSrgb(x) * 255)
          .toString(16)
          .padStart(2, "0")
      )
      .join("")
  )
}
