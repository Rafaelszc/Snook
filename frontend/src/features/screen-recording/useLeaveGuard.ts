import { useCallback, useEffect, useRef } from "react"
import { useBlocker } from "react-router"

import { MESSAGES } from "./messages"

// Gravação só existe na memória da página: sair perde tudo (`screen-recording` 12).
// Devolve `release`, que desarma na hora, antes de navegar para o detalhe.
export function useLeaveGuard(active: boolean): () => void {
  const armed = useRef(active)
  useEffect(() => {
    armed.current = active
  }, [active])

  useEffect(() => {
    if (!active) return
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
    }
    window.addEventListener("beforeunload", onBeforeUnload)
    return () => window.removeEventListener("beforeunload", onBeforeUnload)
  }, [active])

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      armed.current && currentLocation.pathname !== nextLocation.pathname
  )
  useEffect(() => {
    if (blocker.state !== "blocked") return
    if (window.confirm(MESSAGES.leaveConfirm)) blocker.proceed()
    else blocker.reset()
  }, [blocker])

  return useCallback(() => {
    armed.current = false
  }, [])
}
