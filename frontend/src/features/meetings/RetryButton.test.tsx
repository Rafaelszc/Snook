import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import type { Status } from "@/components/surfaces/StatusBadge"
import { server } from "@/test/server"

import type { MeetingDetail } from "./api"
import { detail, MEETING_ID } from "./fixtures"
import { renderMeetings } from "./testing"

const URL = `/api/meetings/${MEETING_ID}`
const FAILED = detail({
  status: "failed",
  failed_stage: "generation",
  error_message: "O provedor recusou a chave.",
})

function shows(meeting: MeetingDetail) {
  server.use(http.get(URL, () => HttpResponse.json(meeting)))
}

function retryAnswers() {
  const calls: number[] = []
  server.use(
    http.post(`${URL}/retry`, () => {
      calls.push(1)
      return HttpResponse.json(
        detail({ status: "transcribed", participants_confirmed: true }),
        { status: 202 }
      )
    })
  )
  return calls
}

it("em failed mostra o motivo e tenta de novo (meetings 42)", async () => {
  shows(FAILED)
  const calls = retryAnswers()
  const { container } = renderMeetings(`/meetings/${MEETING_ID}`)

  expect(await screen.findByText("O provedor recusou a chave.")).toBeVisible()
  expect(screen.getByText("Falhou na etapa: Geração do backlog")).toBeVisible()
  expect(await axe(container)).toHaveNoViolations()
  await userEvent.click(
    screen.getByRole("button", { name: "Tentar novamente" })
  )

  expect(await screen.findByText("Transcrita")).toBeVisible()
  expect(calls).toHaveLength(1)
  expect(screen.queryByRole("button", { name: "Tentar novamente" })).toBeNull()
})

it.each<Status>([
  "pending",
  "processing",
  "transcribed",
  "needs_split",
  "generating",
  "done",
])("sem botão em %s (meetings 42)", async (status) => {
  shows(detail({ status }))
  renderMeetings(`/meetings/${MEETING_ID}`)
  await screen.findByRole("heading", { name: FAILED.title })
  expect(screen.queryByRole("button", { name: "Tentar novamente" })).toBeNull()
})

it("com backlog gravado, confirma antes com o aviso de perda das edições (meetings 42)", async () => {
  shows({ ...FAILED, has_backlog: true })
  const calls = retryAnswers()
  renderMeetings(`/meetings/${MEETING_ID}`)

  await userEvent.click(
    await screen.findByRole("button", { name: "Tentar novamente" })
  )
  const dialog = screen.getByRole("alertdialog", { name: "Tentar novamente?" })
  expect(dialog).toHaveAccessibleDescription(/edições manuais se perdem/)
  expect(dialog).toHaveAttribute("data-slot", "dialog-surface")
  expect(await axe(dialog)).toHaveNoViolations()
  expect(calls).toHaveLength(0)

  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }))
  expect(calls).toHaveLength(0)

  await userEvent.click(
    screen.getByRole("button", { name: "Tentar novamente" })
  )
  const confirm = screen.getAllByRole("button", { name: "Tentar novamente" })
  await userEvent.click(confirm[confirm.length - 1])
  expect(await screen.findByText("Transcrita")).toBeVisible()
  expect(calls).toHaveLength(1)
})

it("409 da API aparece na tela", async () => {
  shows(FAILED)
  server.use(
    http.post(`${URL}/retry`, () =>
      HttpResponse.json(
        {
          error: {
            code: "not_failed",
            message: "Só uma reunião com falha pode ser tentada de novo.",
          },
        },
        { status: 409 }
      )
    )
  )
  renderMeetings(`/meetings/${MEETING_ID}`)

  await userEvent.click(
    await screen.findByRole("button", { name: "Tentar novamente" })
  )
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Só uma reunião com falha pode ser tentada de novo."
  )
})
