import { act, fireEvent, render } from "@testing-library/react"
import { useRef } from "react"
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
  type MockInstance,
} from "vitest"

import { CAN_HOVER_QUERY, REDUCED_MOTION_QUERY } from "./media"
import { stubMatchMedia } from "./matchMediaStub"
import { usePointerSpotlight } from "./usePointerSpotlight"

type AddListener = HTMLElement["addEventListener"]

let renders = 0

function Probe() {
  const ref = useRef<HTMLDivElement>(null)
  usePointerSpotlight(ref)
  renders++
  return <div ref={ref} data-testid="area" />
}

let frames: FrameRequestCallback[] = []

beforeEach(() => {
  renders = 0
  frames = []
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn((cb: FrameRequestCallback) => frames.push(cb))
  )
  vi.stubGlobal("cancelAnimationFrame", vi.fn())
})
afterEach(() => vi.unstubAllGlobals())

const flush = () => act(() => frames.splice(0).forEach((cb) => cb(0)))

// React delega eventos no container; conta só o que vai direto à área.
function pointermoveListeners(spy: MockInstance<AddListener>) {
  return spy.mock.calls.filter(
    ([type], i) =>
      type === "pointermove" &&
      (spy.mock.contexts[i] as HTMLElement).dataset?.testid === "area"
  )
}

describe("usePointerSpotlight", () => {
  it("registra pointermove com hover fino e sem movimento reduzido", () => {
    stubMatchMedia({ [CAN_HOVER_QUERY]: true, [REDUCED_MOTION_QUERY]: false })
    const spy = vi.spyOn(HTMLElement.prototype, "addEventListener")
    render(<Probe />)
    expect(pointermoveListeners(spy)).toHaveLength(1)
    spy.mockRestore()
  })

  it("com pointer: coarse (sem hover fino), nenhum listener", () => {
    stubMatchMedia({ [CAN_HOVER_QUERY]: false, [REDUCED_MOTION_QUERY]: false })
    const spy = vi.spyOn(HTMLElement.prototype, "addEventListener")
    render(<Probe />)
    expect(pointermoveListeners(spy)).toHaveLength(0)
    spy.mockRestore()
  })

  it("com movimento reduzido, nenhum listener", () => {
    stubMatchMedia({ [CAN_HOVER_QUERY]: true, [REDUCED_MOTION_QUERY]: true })
    const spy = vi.spyOn(HTMLElement.prototype, "addEventListener")
    render(<Probe />)
    expect(pointermoveListeners(spy)).toHaveLength(0)
    spy.mockRestore()
  })

  it("remove o listener quando a preferência muda para reduzido", () => {
    const mq = stubMatchMedia({
      [CAN_HOVER_QUERY]: true,
      [REDUCED_MOTION_QUERY]: false,
    })
    const spy = vi.spyOn(HTMLElement.prototype, "removeEventListener")
    render(<Probe />)
    act(() => mq.set(REDUCED_MOTION_QUERY, true))
    expect(pointermoveListeners(spy)).toHaveLength(1)
    spy.mockRestore()
  })

  it("atualiza CSS variables em requestAnimationFrame, sem re-render", () => {
    stubMatchMedia({ [CAN_HOVER_QUERY]: true, [REDUCED_MOTION_QUERY]: false })
    const { getByTestId } = render(<Probe />)
    const area = getByTestId("area")
    area.getBoundingClientRect = () =>
      ({ left: 10, top: 20, width: 100, height: 100 }) as DOMRect
    const before = renders

    fireEvent.pointerMove(area, { clientX: 60, clientY: 90 })
    fireEvent.pointerMove(area, { clientX: 70, clientY: 100 })
    expect(frames).toHaveLength(1) // coalescido em um quadro
    expect(area.style.getPropertyValue("--pointer-x")).toBe("")

    flush()
    expect(area.style.getPropertyValue("--pointer-x")).toBe("60px")
    expect(area.style.getPropertyValue("--pointer-y")).toBe("80px")
    expect(renders).toBe(before)
  })

  it("cancela o quadro pendente ao desmontar", () => {
    stubMatchMedia({ [CAN_HOVER_QUERY]: true, [REDUCED_MOTION_QUERY]: false })
    const { getByTestId, unmount } = render(<Probe />)
    fireEvent.pointerMove(getByTestId("area"), { clientX: 1, clientY: 1 })
    unmount()
    expect(cancelAnimationFrame).toHaveBeenCalled()
  })
})
