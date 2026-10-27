import { act, render, renderHook, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, Link, RouterProvider } from "react-router"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { axe } from "vitest-axe"

import {
  endTrack,
  fakeAudioContext,
  fakeMediaRecorder,
  fakeStream,
} from "./capture/fakes"
import { systemClock } from "./capture/media"
import { mixSources } from "./capture/mixer"
import { createRecorder, MAX_RECORDING_SECONDS } from "./capture/recorder"
import { MESSAGES } from "./messages"
import { RecordingPanel } from "./RecordingPanel"
import { formatElapsed } from "./useElapsed"
import { useLeaveGuard } from "./useLeaveGuard"
import { useRecording } from "./useRecording"

function setup() {
  const media = fakeMediaRecorder()
  const audio = fakeAudioContext()
  const recorder = createRecorder(media.ctor)
  const mix = (sources: Parameters<typeof mixSources>[0]) =>
    mixSources(sources, () => audio.context)
  const hook = renderHook(() =>
    useRecording({ recorder, mix, clock: systemClock })
  )
  return { ...hook, media, audio }
}

function liveTracks(...streams: MediaStream[]) {
  return streams
    .flatMap((s) => s.getTracks())
    .filter((t) => t.readyState === "live")
}

describe("useRecording", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it("parar entrega o áudio e encerra tela e microfone (screen-recording 8, 13)", async () => {
    const display = fakeStream({ audio: true, video: true })
    const mic = fakeStream({ audio: true })
    const { result, media, audio } = setup()

    act(() => result.current.begin({ display, mic }))
    expect(result.current.state.kind).toBe("recording")
    media.instances[0]?.emit(new Blob(["opus"]))

    await act(() => result.current.stop())
    const state = result.current.state
    expect(state.kind).toBe("stopped")
    if (state.kind !== "stopped") return
    expect(await state.recording.blob.text()).toBe("opus")
    expect(state.recording.limitReached).toBe(false)
    expect(liveTracks(display, mic)).toEqual([])
    expect(audio.closed).toBe(true)
  })

  it("para sozinho em 1h59m50s com aviso de limite (screen-recording 10)", async () => {
    const { result } = setup()
    act(() => result.current.begin({ mic: fakeStream({ audio: true }) }))
    const startedAt = Date.now()

    await act(() =>
      vi.advanceTimersByTimeAsync(MAX_RECORDING_SECONDS * 1000 - 1)
    )
    expect(result.current.state.kind).toBe("recording")
    await act(() => vi.advanceTimersByTimeAsync(1))

    const state = result.current.state
    expect(state.kind).toBe("stopped")
    if (state.kind !== "stopped") return
    expect(state.recording.limitReached).toBe(true)
    expect(Date.now() - startedAt).toBe(MAX_RECORDING_SECONDS * 1000)
  })

  it("fim do compartilhamento pelo navegador equivale a Parar (screen-recording 11)", async () => {
    const display = fakeStream({ audio: true, video: true })
    const mic = fakeStream({ audio: true })
    const { result } = setup()
    act(() => result.current.begin({ display, mic }))

    const video = display.getVideoTracks()[0]
    if (!video) throw new Error("sem vídeo")
    await act(async () => endTrack(video))

    const state = result.current.state
    expect(state.kind).toBe("stopped")
    if (state.kind !== "stopped") return
    expect(state.recording.limitReached).toBe(false)
    expect(liveTracks(display, mic)).toEqual([])
  })

  it("parar duas vezes não quebra", async () => {
    const { result } = setup()
    act(() => result.current.begin({ mic: fakeStream({ audio: true }) }))
    await act(async () => {
      await Promise.all([result.current.stop(), result.current.stop()])
    })
    expect(result.current.state.kind).toBe("stopped")
  })

  it("sair da tela no meio da gravação encerra tela e microfone", () => {
    const display = fakeStream({ audio: true, video: true })
    const mic = fakeStream({ audio: true })
    const { result, unmount } = setup()
    act(() => result.current.begin({ display, mic }))
    unmount()
    expect(liveTracks(display, mic)).toEqual([])
  })

  it("falha ao iniciar o gravador encerra as fontes", () => {
    const display = fakeStream({ audio: true, video: true })
    const recorder = {
      start: () => {
        throw new Error("NotSupportedError")
      },
      stop: () => Promise.reject(new Error("not started")),
    }
    const audio = fakeAudioContext()
    const { result } = renderHook(() =>
      useRecording({
        recorder,
        mix: (s) => mixSources(s, () => audio.context),
        clock: systemClock,
      })
    )
    act(() => result.current.begin({ display }))
    expect(result.current.state).toEqual({
      kind: "failed",
      message: MESSAGES.recordFailed,
    })
    expect(liveTracks(display)).toEqual([])
  })
})

describe("RecordingPanel", () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it("mostra o tempo decorrido e Parar (screen-recording 8)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const onStop = vi.fn()
    render(
      <RecordingPanel
        startedAt={Date.now()}
        clock={systemClock}
        stopping={false}
        onStop={onStop}
      />
    )
    expect(screen.getByRole("timer")).toHaveTextContent("0:00:00")
    await act(() => vi.advanceTimersByTimeAsync(65_000))
    expect(screen.getByRole("timer")).toHaveTextContent("0:01:05")
    expect(screen.getByRole("status")).toHaveTextContent(MESSAGES.recording)

    vi.useRealTimers()
    expect(await axe(document.body)).toHaveNoViolations()
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.stop }))
    expect(onStop).toHaveBeenCalledOnce()
  })

  it("desabilita Parar enquanto para", () => {
    render(
      <RecordingPanel
        startedAt={Date.now()}
        clock={systemClock}
        stopping
        onStop={() => {}}
      />
    )
    expect(
      screen.getByRole("button", { name: MESSAGES.stopping })
    ).toBeDisabled()
  })

  it.each([
    [0, "0:00:00"],
    [59, "0:00:59"],
    [3600, "1:00:00"],
    [MAX_RECORDING_SECONDS, "1:59:50"],
  ])("formata %i s como %s", (seconds, text) => {
    expect(formatElapsed(seconds)).toBe(text)
  })
})

describe("useLeaveGuard (screen-recording 12)", () => {
  function Guarded({ active }: { active: boolean }) {
    useLeaveGuard(active)
    return <Link to="/other">sair</Link>
  }

  function renderGuard(active: boolean) {
    const router = createMemoryRouter(
      [
        { path: "/", element: <Guarded active={active} /> },
        { path: "/other", element: <p>outra</p> },
      ],
      { initialEntries: ["/"] }
    )
    render(<RouterProvider router={router} />)
    return router
  }

  function unload() {
    const event = new Event("beforeunload", { cancelable: true })
    window.dispatchEvent(event)
    return event.defaultPrevented
  }

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fechar a página pede confirmação do navegador", () => {
    renderGuard(true)
    expect(unload()).toBe(true)
  })

  it("sem gravação pendente, não pede", () => {
    renderGuard(false)
    expect(unload()).toBe(false)
  })

  it("navegar no app pede confirmação; recusar fica na tela", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false)
    const router = renderGuard(true)
    await userEvent.click(screen.getByRole("link", { name: "sair" }))
    expect(confirm).toHaveBeenCalledWith(MESSAGES.leaveConfirm)
    expect(router.state.location.pathname).toBe("/")
  })

  it("aceitar a confirmação sai", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true)
    const router = renderGuard(true)
    await userEvent.click(screen.getByRole("link", { name: "sair" }))
    expect(await screen.findByText("outra")).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/other")
  })
})
