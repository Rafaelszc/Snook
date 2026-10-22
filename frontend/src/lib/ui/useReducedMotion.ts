import { REDUCED_MOTION_QUERY } from "./media"
import { useMediaQuery } from "./useMediaQuery"

// Concorda com a media query de motion.css.
export function useReducedMotion(): boolean {
  return useMediaQuery(REDUCED_MOTION_QUERY, true)
}
