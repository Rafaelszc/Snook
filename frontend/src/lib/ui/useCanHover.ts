import { CAN_HOVER_QUERY } from "./media"
import { useMediaQuery } from "./useMediaQuery"

export function useCanHover(): boolean {
  return useMediaQuery(CAN_HOVER_QUERY, false)
}
