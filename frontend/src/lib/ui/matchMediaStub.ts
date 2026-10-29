import { vi } from "vitest"

// Só para testes: matchMedia controlável por consulta.
export function stubMatchMedia(matches: Record<string, boolean>) {
  const listeners = new Map<string, Set<() => void>>()
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      get matches() {
        return matches[query] ?? false
      },
      media: query,
      addEventListener: (_: string, cb: () => void) => {
        if (!listeners.has(query)) listeners.set(query, new Set())
        listeners.get(query)!.add(cb)
      },
      removeEventListener: (_: string, cb: () => void) => {
        listeners.get(query)?.delete(cb)
      },
    }))
  )
  return {
    set(query: string, value: boolean) {
      matches[query] = value
      listeners.get(query)?.forEach((cb) => cb())
    },
  }
}
