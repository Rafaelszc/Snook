import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { describe, expect, it, vi } from "vitest"
import { axe } from "vitest-axe"

import { server } from "@/test/server"

import { recordingFileName } from "./fileName"
import { MESSAGES } from "./messages"
import { SendRecordingPage } from "./SendRecordingPage"
import type { Recording } from "./useRecording"

// 27/10/2026 09:05 na hora local.
const STARTED_AT = new Date(2026, 9, 27, 9, 5, 42).getTime()
const NAME = "gravacao-2026-10-27-09h05.webm"
const CREATED = { id: "m-rec", title: NAME, status: "pending" }

function recording(over: Partial<Recording> = {}): Recording {
  return {
    blob: new Blob(["opus"], { type: "audio/webm" }),
    startedAt: STARTED_AT,
    limitReached: false,
    ...over,
  }
}

function renderSend(rec = recording()) {
  const onSent = vi.fn()
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const view = render(
    <QueryClientProvider client={queryClient}>
      <SendRecordingPage recording={rec} onSent={onSent} />
    </QueryClientProvider>
  )
  return { ...view, onSent }
}

describe("recordingFileName (screen-recording 14)", () => {
  it("usa data e hora locais do início", () => {
    expect(recordingFileName(STARTED_AT)).toBe(NAME)
  })

  it("completa com zero à esquerda", () => {
    expect(recordingFileName(new Date(2027, 0, 3, 0, 0).getTime())).toBe(
      "gravacao-2027-01-03-00h00.webm"
    )
  })
})

describe("SendRecordingPage", () => {
  it("título vem do nome do arquivo e é editável; envia título e participantes (screen-recording 15, 16, 17, 20)", async () => {
    let sent = ""
    server.use(
      http.post("/api/meetings", async ({ request }) => {
        sent = await request.text()
        return HttpResponse.json(CREATED, { status: 201 })
      })
    )
    const { container, onSent } = renderSend()

    const title = screen.getByLabelText(MESSAGES.title)
    expect(title).toHaveValue(NAME)
    expect(screen.getByText(NAME)).toBeInTheDocument()
    await userEvent.clear(title)
    await userEvent.type(title, "Planejamento")
    await userEvent.type(screen.getByLabelText(MESSAGES.speakers), "3")
    expect(await axe(container)).toHaveNoViolations()
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.send }))

    await waitFor(() => expect(onSent).toHaveBeenCalledWith("m-rec"))
    expect(sent).toContain(`filename="${NAME}"`)
    expect(sent).toContain("Content-Type: audio/webm")
    expect(sent).toMatch(/name="title"\r\n\r\nPlanejamento\r\n/)
    expect(sent).toMatch(/name="expected_speakers"\r\n\r\n3\r\n/)
  })

  it("título vazio não vai no corpo: o servidor usa o nome do arquivo", async () => {
    let sent = ""
    server.use(
      http.post("/api/meetings", async ({ request }) => {
        sent = await request.text()
        return HttpResponse.json(CREATED, { status: 201 })
      })
    )
    const { onSent } = renderSend()
    await userEvent.clear(screen.getByLabelText(MESSAGES.title))
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.send }))
    await waitFor(() => expect(onSent).toHaveBeenCalled())
    expect(sent).not.toContain('name="title"')
    expect(sent).not.toContain('name="expected_speakers"')
  })

  it("recusa do servidor mostra a mensagem da API (screen-recording 18)", async () => {
    server.use(
      http.post("/api/meetings", () =>
        HttpResponse.json(
          {
            error: {
              code: "audio_too_long",
              message: "A gravação passa de 2 horas, o limite de duração.",
            },
          },
          { status: 422 }
        )
      )
    )
    const { onSent } = renderSend()
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.send }))
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A gravação passa de 2 horas, o limite de duração."
    )
    expect(
      screen.queryByRole("button", { name: MESSAGES.retry })
    ).not.toBeInTheDocument()
    expect(onSent).not.toHaveBeenCalled()
  })

  it("erro de campo aparece junto do campo (screen-recording 16)", async () => {
    server.use(
      http.post("/api/meetings", () =>
        HttpResponse.json(
          {
            error: {
              code: "validation_error",
              message: "Dados inválidos.",
              fields: { expected_speakers: "Informe de 1 a 20." },
            },
          },
          { status: 422 }
        )
      )
    )
    renderSend()
    await userEvent.type(screen.getByLabelText(MESSAGES.speakers), "30")
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.send }))
    expect(await screen.findByText("Informe de 1 a 20.")).toBeInTheDocument()
    expect(screen.getByLabelText(MESSAGES.speakers)).toHaveAttribute(
      "aria-invalid",
      "true"
    )
  })

  it("falha de rede mostra Tentar de novo, que reenvia a mesma gravação (screen-recording 19)", async () => {
    const bodies: string[] = []
    let fail = true
    server.use(
      http.post("/api/meetings", async ({ request }) => {
        bodies.push(await request.text())
        if (fail) return HttpResponse.error()
        return HttpResponse.json(CREATED, { status: 201 })
      })
    )
    const { onSent } = renderSend()
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.send }))

    expect(await screen.findByRole("alert")).toHaveTextContent(
      MESSAGES.networkError
    )
    fail = false
    await userEvent.click(screen.getByRole("button", { name: MESSAGES.retry }))

    await waitFor(() => expect(onSent).toHaveBeenCalledWith("m-rec"))
    expect(bodies).toHaveLength(2)
    expect(bodies[1]).toContain("opus")
    expect(bodies[1]).toContain(`filename="${NAME}"`)
  })

  it("parada no limite mostra o aviso (screen-recording 10)", () => {
    renderSend(recording({ limitReached: true }))
    expect(screen.getByText(MESSAGES.limitReached)).toBeInTheDocument()
  })

  it("sem parada no limite, sem aviso", () => {
    renderSend()
    expect(screen.queryByText(MESSAGES.limitReached)).not.toBeInTheDocument()
  })
})
