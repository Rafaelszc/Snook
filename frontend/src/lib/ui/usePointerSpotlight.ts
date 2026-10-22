import { useEffect, type RefObject } from "react"

import { useCanHover } from "./useCanHover"
import { useReducedMotion } from "./useReducedMotion"

// Mouse-tracking (ADR-0022): só hover fino e sem movimento reduzido. Grava
// --pointer-x/--pointer-y no elemento por requestAnimationFrame, sem re-render.
export function usePointerSpotlight(ref: RefObject<HTMLElement | null>) {
  const canHover = useCanHover()
  const reduced = useReducedMotion()
  const enabled = canHover && !reduced

  useEffect(() => {
    const el = ref.current
    if (!enabled || !el) return

    let frame = 0
    let x = 0
    let y = 0

    const paint = () => {
      frame = 0
      const rect = el.getBoundingClientRect()
      el.style.setProperty("--pointer-x", `${x - rect.left}px`)
      el.style.setProperty("--pointer-y", `${y - rect.top}px`)
    }
    const onMove = (e: PointerEvent) => {
      x = e.clientX
      y = e.clientY
      if (!frame) frame = requestAnimationFrame(paint)
    }

    el.addEventListener("pointermove", onMove, { passive: true })
    return () => {
      el.removeEventListener("pointermove", onMove)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [ref, enabled])
}
