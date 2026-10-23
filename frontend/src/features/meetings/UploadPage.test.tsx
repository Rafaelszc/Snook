import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { CONSENT_NOTICE_TEXT } from "@/components/surfaces/ConsentNotice/messages"
import { server } from "@/test/server"

import { detail, MEETING_ID, SUMMARY } from "./fixtures"
import { TOO_LARGE, UNSUPPORTED_FORMAT } from "./messages"
import { renderMeetings } from "./testing"
import { MAX_UPLOAD_BYTES } from "./validateFile"

function audio(name = "reuniao-semanal.mp3", size = 16) {
  return new File([new Uint8Array(size)], name, { type: "audio/mpeg" })
}

function sized(name: string, size: number) {
  const file = audio(name, 1)
  Object.defineProperty(file, "size", { value: size })
  return file
}

// applyAccept: false deixa o teste escolher extensão fora da lista, como num arrastar.
const user = () => userEvent.setup({ applyAccept: false })

it("aceita arquivo, título e participantes e mostra o envio (meetings 35, 36)", async () => {
  // jsdom e undici têm File diferentes: o corpo multipart é lido como texto.
  let sent: string | null = null
  let release = () => {}
  const gate = new Promise<void>((resolve) => (release = resolve))
  server.use(
    http.post("/api/meetings", async ({ request }) => {
      sent = await request.text()
      await gate
      return HttpResponse.json(SUMMARY, { status: 201 })
    }),
    http.get(`/api/meetings/${MEETING_ID}`, () => HttpResponse.json(detail()))
  )
  const { container } = renderMeetings("/meetings/new")

  await user().upload(screen.getByLabelText("Arquivo da reunião"), audio())
  const title = screen.getByLabelText("Título")
  expect(title).toHaveValue("reuniao-semanal.mp3")
  await user().clear(title)
  await user().type(title, "Semanal")
  await user().type(screen.getByLabelText("Número de participantes"), "4")
  expect(await axe(container)).toHaveNoViolations()
  await user().click(screen.getByRole("button", { name: "Enviar" }))

  expect(
    await screen.findByRole("button", { name: "Enviando…" })
  ).toBeDisabled()
  expect(
    screen.getByRole("progressbar", { name: "Progresso do envio" })
  ).toBeVisible()
  release()

  await waitFor(() => expect(sent).not.toBeNull())
  const body = sent as unknown as string
  expect(body).toContain('name="file"; filename="reuniao-semanal.mp3"')
  expect(body).toMatch(/name="title"\r\n\r\nSemanal\r\n/)
  expect(body).toMatch(/name="expected_speakers"\r\n\r\n4\r\n/)
})

it("depois do upload leva ao detalhe da nova reunião (meetings 39)", async () => {
  server.use(
    http.post("/api/meetings", () =>
      HttpResponse.json(SUMMARY, { status: 201 })
    ),
    http.get(`/api/meetings/${MEETING_ID}`, () => HttpResponse.json(detail()))
  )
  const { router } = renderMeetings("/meetings/new")

  await user().upload(screen.getByLabelText("Arquivo da reunião"), audio())
  await user().click(screen.getByRole("button", { name: "Enviar" }))

  await waitFor(() =>
    expect(router.state.location.pathname).toBe(`/meetings/${MEETING_ID}`)
  )
  expect(
    await screen.findByRole("heading", { name: SUMMARY.title })
  ).toBeInTheDocument()
})

it.each([
  ["extensão fora da lista", sized("notas.txt", 10), UNSUPPORTED_FORMAT],
  [
    "acima de 524.288.000 bytes",
    sized("longa.mp3", MAX_UPLOAD_BYTES + 1),
    TOO_LARGE,
  ],
])("recusa antes de enviar: %s (meetings 37)", async (_, file, message) => {
  let called = false
  server.use(
    http.post("/api/meetings", () => {
      called = true
      return HttpResponse.json(SUMMARY, { status: 201 })
    })
  )
  renderMeetings("/meetings/new")

  await user().upload(screen.getByLabelText("Arquivo da reunião"), file)
  expect(screen.getByText(message)).toBeVisible()
  expect(screen.getByLabelText("Arquivo da reunião")).toBeInvalid()
  await user().click(screen.getByRole("button", { name: "Enviar" }))

  expect(called).toBe(false)
})

it("aceita arquivo com exatamente o limite de bytes", async () => {
  renderMeetings("/meetings/new")
  await user().upload(
    screen.getByLabelText("Arquivo da reunião"),
    sized("limite.wav", MAX_UPLOAD_BYTES)
  )
  expect(screen.queryByText(TOO_LARGE)).toBeNull()
  expect(screen.getByLabelText("Título")).toHaveValue("limite.wav")
})

it.each([
  [
    {
      code: "no_audio",
      message: "Arquivo sem áudio: não há trilha de áudio legível.",
    },
    422,
  ],
  [
    {
      code: "payload_too_large",
      message: "O arquivo passa de 500 MB, o limite de tamanho.",
    },
    413,
  ],
])("mostra erro devolvido pela API (meetings 38)", async (error, status) => {
  server.use(
    http.post("/api/meetings", () =>
      HttpResponse.json({ error: { ...error, fields: {} } }, { status })
    )
  )
  renderMeetings("/meetings/new")

  await user().upload(screen.getByLabelText("Arquivo da reunião"), audio())
  await user().click(screen.getByRole("button", { name: "Enviar" }))

  expect(await screen.findByRole("alert")).toHaveTextContent(error.message)
  expect(screen.getByRole("button", { name: "Enviar" })).toBeEnabled()
})

it("erro de campo da API aparece junto do campo (meetings 38)", async () => {
  const message = "Informe de 1 a 20 participantes."
  server.use(
    http.post("/api/meetings", () =>
      HttpResponse.json(
        {
          error: {
            code: "invalid_expected_speakers",
            message,
            fields: { expected_speakers: message },
          },
        },
        { status: 422 }
      )
    )
  )
  renderMeetings("/meetings/new")

  await user().upload(screen.getByLabelText("Arquivo da reunião"), audio())
  await user().type(screen.getByLabelText("Número de participantes"), "30")
  await user().click(screen.getByRole("button", { name: "Enviar" }))

  const field = await screen.findByLabelText("Número de participantes")
  await waitFor(() => expect(field).toBeInvalid())
  expect(field).toHaveAccessibleDescription(message)
})

it("o aviso de consentimento fica junto do botão, só texto (meetings 52, Q71)", async () => {
  renderMeetings("/meetings/new")
  const notice = screen.getByTestId("consent-notice")
  expect(notice).toHaveTextContent(CONSENT_NOTICE_TEXT)
  expect(notice).toBeVisible()
  const send = screen.getByRole("button", { name: "Enviar" })
  expect(notice.parentElement).toContainElement(send)
  expect(send).toBeEnabled()
})
