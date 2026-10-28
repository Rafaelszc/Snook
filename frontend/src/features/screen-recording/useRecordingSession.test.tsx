import { act, render, renderHook, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"
import { axe } from "vitest-axe"

import { fakeCapture, fakeStream } from "./capture/fakes"
import { MESSAGES } from "./messages"
import { SourceWarningDialog } from "./SourceWarningDialog"
import { useRecordingSession } from "./useRecordingSession"

function setup(
  display: ReturnType<typeof fakeCapture>,
  mic: ReturnType<typeof fakeCapture>
) {
  return renderHook(() => useRecordingSession({ display, mic }))
}

async function start(result: { current: { start: () => Promise<void> } }) {
  await act(() => result.current.start())
}

describe("useRecordingSession", () => {
  it("pede a tela antes do microfone (screen-recording 2)", async () => {
    const order: string[] = []
    const display = fakeCapture(fakeStream({ audio: true }), () =>
      order.push("display")
    )
    const mic = fakeCapture(fakeStream({ audio: true }), () =>
      order.push("mic")
    )
    const { result } = setup(display, mic)
    await start(result)
    expect(order).toEqual(["display", "mic"])
  })

  it("com as duas fontes fica pronto sem aviso (screen-recording 3)", async () => {
    const screenStream = fakeStream({ audio: true })
    const micStream = fakeStream({ audio: true })
    const { result } = setup(fakeCapture(screenStream), fakeCapture(micStream))
    await start(result)
    expect(result.current.state).toEqual({
      kind: "ready",
      sources: { display: screenStream, mic: micStream },
    })
  })

  it.each([
    ["tela sem trilha de áudio", fakeStream({ audio: false })],
    ["compartilhamento negado", new DOMException("no", "NotAllowedError")],
  ])(
    "sem som da tela avisa e espera (screen-recording 4): %s",
    async (_, d) => {
      const micStream = fakeStream({ audio: true })
      const { result } = setup(fakeCapture(d), fakeCapture(micStream))
      await start(result)
      expect(result.current.state).toEqual({
        kind: "missing",
        missing: "display",
      })
      expect(micStream.getTracks()[0]?.readyState).toBe("live")

      act(() => result.current.confirm())
      expect(result.current.state).toEqual({
        kind: "ready",
        sources: { mic: micStream },
      })
    }
  )

  it("sem microfone avisa e espera (screen-recording 5)", async () => {
    const screenStream = fakeStream({ audio: true })
    const { result } = setup(
      fakeCapture(screenStream),
      fakeCapture(new DOMException("no", "NotAllowedError"))
    )
    await start(result)
    expect(result.current.state).toEqual({ kind: "missing", missing: "mic" })

    act(() => result.current.confirm())
    expect(result.current.state).toEqual({
      kind: "ready",
      sources: { display: screenStream },
    })
  })

  it("sem nenhuma fonte recusa e encerra a tela (screen-recording 6)", async () => {
    const screenStream = fakeStream({ audio: false })
    const { result } = setup(
      fakeCapture(screenStream),
      fakeCapture(new DOMException("no", "NotFoundError"))
    )
    await start(result)
    expect(result.current.state).toEqual({
      kind: "refused",
      message: MESSAGES.noSource,
    })
    for (const track of screenStream.getTracks()) {
      expect(track.readyState).toBe("ended")
    }
  })

  it("cancelar encerra tela e microfone (screen-recording 7)", async () => {
    const screenStream = fakeStream({ audio: true })
    const { result } = setup(
      fakeCapture(screenStream),
      fakeCapture(new DOMException("no", "NotAllowedError"))
    )
    await start(result)
    act(() => result.current.cancel())
    expect(result.current.state).toEqual({ kind: "idle" })
    for (const track of screenStream.getTracks()) {
      expect(track.readyState).toBe("ended")
    }
  })
})

describe("SourceWarningDialog", () => {
  it.each([
    ["display", MESSAGES.missingDisplay, MESSAGES.micOnly],
    ["mic", MESSAGES.missingMic, MESSAGES.displayOnly],
  ] as const)("nomeia a fonte ausente: %s", async (missing, text, confirm) => {
    const calls: string[] = []
    render(
      <SourceWarningDialog
        missing={missing}
        browser="chrome"
        onConfirm={() => calls.push("confirm")}
        onCancel={() => calls.push("cancel")}
      />
    )
    expect(screen.getByRole("alertdialog")).toHaveTextContent(text)
    expect(await axe(document.body)).toHaveNoViolations()

    await userEvent.click(screen.getByRole("button", { name: confirm }))
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.cancel }))
    expect(calls).toEqual(["confirm", "cancel"])
  })

  it("Escape cancela", async () => {
    const calls: string[] = []
    render(
      <SourceWarningDialog
        missing="mic"
        browser="chrome"
        onConfirm={() => calls.push("confirm")}
        onCancel={() => calls.push("cancel")}
      />
    )
    await userEvent.keyboard("{Escape}")
    expect(calls).toEqual(["cancel"])
  })
})
