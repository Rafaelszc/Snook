import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { CAN_HOVER_QUERY, REDUCED_MOTION_QUERY } from "./media"
import { stubMatchMedia } from "./matchMediaStub"
import { useCanHover } from "./useCanHover"
import { useReducedMotion } from "./useReducedMotion"

afterEach(() => vi.unstubAllGlobals())

describe("useReducedMotion", () => {
  it("segue prefers-reduced-motion e reage a mudança", () => {
    const mq = stubMatchMedia({ [REDUCED_MOTION_QUERY]: false })
    const { result } = renderHook(() => useReducedMotion())
    expect(result.current).toBe(false)
    act(() => mq.set(REDUCED_MOTION_QUERY, true))
    expect(result.current).toBe(true)
  })

  it("sem matchMedia, assume movimento reduzido (seguro)", () => {
    vi.stubGlobal("matchMedia", undefined)
    const { result } = renderHook(() => useReducedMotion())
    expect(result.current).toBe(true)
  })
})

describe("useCanHover", () => {
  it("segue (hover: hover) and (pointer: fine)", () => {
    const mq = stubMatchMedia({ [CAN_HOVER_QUERY]: true })
    const { result } = renderHook(() => useCanHover())
    expect(result.current).toBe(true)
    act(() => mq.set(CAN_HOVER_QUERY, false))
    expect(result.current).toBe(false)
  })

  it("sem matchMedia, assume sem hover (seguro)", () => {
    vi.stubGlobal("matchMedia", undefined)
    const { result } = renderHook(() => useCanHover())
    expect(result.current).toBe(false)
  })
})
