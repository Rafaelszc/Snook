import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { createMemoryRouter, RouterProvider } from "react-router"
import { describe, expect, it } from "vitest"
import { axe } from "vitest-axe"

import { CONSENT_NOTICE_TEXT } from "@/components/surfaces/ConsentNotice/messages"
import { server } from "@/test/server"

import {
  fakeAudioContext,
  fakeBrowserEnv,
  fakeCapture,
  fakeMediaRecorder,
  fakeStream,
} from "./capture/fakes"
import { systemClock } from "./capture/media"
import { mixSources } from "./capture/mixer"
import { createRecorder } from "./capture/recorder"
import { MESSAGES } from "./messages"
import { RecordPage, type RecordDeps } from "./RecordPage"

const GLASS = '[data-slot="glass-panel"]'

function renderRecord(deps: Partial<RecordDeps> = {}) {
  const media = fakeMediaRecorder()
  const audio = fakeAudioContext()
  const display = fakeStream({ audio: true, video: true })
  const mic = fakeStream({ audio: true })
  const router = createMemoryRouter(
    [
      {
        path: "/meetings/record",
        element: (
          <RecordPage
            deps={{
              env: fakeBrowserEnv(),
              display: fakeCapture(display),
              mic: fakeCapture(mic),
              recorder: createRecorder(media.ctor),
              mix: (s) => mixSources(s, () => audio.context),
              clock: systemClock,
              ...deps,
            }}
          />
        ),
      },
      { path: "/meetings/new", element: <h1>Upload</h1> },
      { path: "/meetings/:id", element: <h1>Detalhe</h1> },
    ],
    { initialEntries: ["/meetings/record"] }
  )
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
  return { ...view, router, media, display, mic }
}

const recordButton = () => screen.getByRole("button", { name: MESSAGES.record })

describe("RecordPage", () => {
  it("aviso de consentimento junto do botão, só texto (screen-recording 26)", async () => {
    const { container } = renderRecord()
    const notice = screen.getByTestId("consent-notice")
    expect(notice).toHaveTextContent(CONSENT_NOTICE_TEXT)
    expect(notice.textContent?.trim()).toBe(CONSENT_NOTICE_TEXT)
    expect(within(notice).queryByRole("checkbox")).not.toBeInTheDocument()
    expect(notice.parentElement).toContainElement(recordButton())
    expect(recordButton()).toBeEnabled()
    expect(await axe(container)).toHaveNoViolations()
  })

  it("oferece também o envio de arquivo (screen-recording 1)", async () => {
    const { router } = renderRecord()
    await userEvent.click(
      screen.getByRole("link", { name: MESSAGES.uploadInstead })
    )
    expect(router.state.location.pathname).toBe("/meetings/new")
  })

  it("fora de contexto seguro desabilita com a mensagem do critério 27", () => {
    renderRecord({
      env: fakeBrowserEnv({ secure: false, displayMedia: false }),
    })
    expect(recordButton()).toBeDisabled()
    expect(recordButton()).toHaveAccessibleDescription(MESSAGES.insecure)
    expect(screen.queryByText(MESSAGES.unsupported)).not.toBeInTheDocument()
  })

  it("sem as APIs desabilita e indica Chrome ou Edge (screen-recording 22)", () => {
    renderRecord({ env: fakeBrowserEnv({ webm: false }) })
    expect(recordButton()).toBeDisabled()
    expect(recordButton()).toHaveAccessibleDescription(MESSAGES.unsupported)
  })

  it("outro navegador avisa sem bloquear (screen-recording 23)", () => {
    renderRecord({ env: fakeBrowserEnv({ browser: "other" }) })
    expect(recordButton()).toHaveAccessibleDescription(MESSAGES.unofficial)
    expect(recordButton()).toBeEnabled()
  })

  it("grava, para e envia; leva ao detalhe (screen-recording 2, 3, 8, 13, 14, 17, 20)", async () => {
    let sent = ""
    server.use(
      http.post("/api/meetings", async ({ request }) => {
        sent = await request.text()
        return HttpResponse.json(
          { id: "m-rec", title: "x", status: "pending" },
          { status: 201 }
        )
      })
    )
    const { container, router, media, display, mic } = renderRecord()
    await userEvent.click(recordButton())

    const panel = await screen.findByRole("region", { name: MESSAGES.panel })
    expect(within(panel).getByRole("timer")).toHaveTextContent("0:00:00")
    expect(screen.getByTestId("recording-indicator")).toHaveClass(
      "motion-pulse"
    )
    expect(recordButton()).toBeDisabled()
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
    expect(container.querySelectorAll(GLASS).length).toBeLessThanOrEqual(3)
    expect(await axe(container)).toHaveNoViolations()

    media.instances[0]?.emit(new Blob(["opus"]))
    await userEvent.click(
      within(panel).getByRole("button", { name: MESSAGES.stop })
    )

    const title = await screen.findByLabelText(MESSAGES.title)
    expect((title as HTMLInputElement).value).toMatch(
      /^gravacao-\d{4}-\d{2}-\d{2}-\d{2}h\d{2}\.webm$/
    )
    for (const track of [...display.getTracks(), ...mic.getTracks()]) {
      expect(track.readyState).toBe("ended")
    }

    await userEvent.click(screen.getByRole("button", { name: MESSAGES.send }))
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/meetings/m-rec")
    )
    expect(sent).toContain("opus")
  })

  it("fonte ausente abre o aviso; confirmar grava só com o microfone (screen-recording 4)", async () => {
    const mic = fakeStream({ audio: true })
    renderRecord({
      display: fakeCapture(fakeStream({ audio: false, video: true })),
      mic: fakeCapture(mic),
    })
    await userEvent.click(recordButton())

    const dialog = await screen.findByRole("alertdialog")
    expect(dialog).toHaveTextContent(MESSAGES.missingDisplay)
    expect(document.querySelectorAll(GLASS).length).toBeLessThanOrEqual(3)
    await userEvent.click(
      within(dialog).getByRole("button", { name: MESSAGES.micOnly })
    )
    expect(
      await screen.findByRole("region", { name: MESSAGES.panel })
    ).toBeInTheDocument()
  })

  it("cancelar no aviso não grava e volta ao início (screen-recording 7)", async () => {
    const { media } = renderRecord({
      mic: fakeCapture(new DOMException("no", "NotAllowedError")),
    })
    await userEvent.click(recordButton())
    await userEvent.click(
      await screen.findByRole("button", { name: MESSAGES.cancel })
    )
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
    expect(media.instances).toHaveLength(0)
    expect(recordButton()).toBeEnabled()
  })

  it("sem nenhuma fonte recusa com mensagem (screen-recording 6)", async () => {
    const { media } = renderRecord({
      display: fakeCapture(new DOMException("no", "NotAllowedError")),
      mic: fakeCapture(new DOMException("no", "NotFoundError")),
    })
    await userEvent.click(recordButton())
    expect(await screen.findByRole("alert")).toHaveTextContent(
      MESSAGES.noSource
    )
    expect(media.instances).toHaveLength(0)
  })
})
