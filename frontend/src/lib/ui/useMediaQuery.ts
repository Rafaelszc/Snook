import { useSyncExternalStore } from "react"

// Sem matchMedia, devolve `fallback` (valor seguro para cada consulta).
export function useMediaQuery(query: string, fallback: boolean): boolean {
  return useSyncExternalStore(
    (notify) => {
      if (typeof matchMedia !== "function") return () => {}
      const mq = matchMedia(query)
      mq.addEventListener("change", notify)
      return () => mq.removeEventListener("change", notify)
    },
    () =>
      typeof matchMedia === "function" ? matchMedia(query).matches : fallback,
    () => fallback
  )
}
