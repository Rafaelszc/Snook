import { readdirSync, readFileSync } from "node:fs"
import { join, relative } from "node:path"

import { render, screen } from "@testing-library/react"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { ConsentNotice } from "./ConsentNotice"
import { CONSENT_NOTICE_TEXT } from "./messages"

const SRC = join(import.meta.dirname, "..", "..", "..")
const PHRASE = "obtenha o consentimento de todos os participantes"

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) return sourceFiles(path)
    return /\.(ts|tsx)$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)
      ? [path]
      : []
  })
}

it("a constante tem exatamente o texto do critério (meetings 52)", () => {
  expect(CONSENT_NOTICE_TEXT).toBe(
    "Antes de gravar ou enviar, obtenha o consentimento de todos os participantes da reunião (LGPD). O áudio fica só neste servidor; o texto da transcrição vai ao provedor de LLM ativo."
  )
})

it("mostra só o texto, sem checkbox nem confirmação (Q71)", async () => {
  const { container } = render(<ConsentNotice />)
  const notice = screen.getByTestId("consent-notice")
  expect(notice).toHaveTextContent(CONSENT_NOTICE_TEXT)
  expect(notice).toBeVisible()
  expect(container.querySelector("input, button, [role=checkbox]")).toBeNull()
  expect(await axe(container)).toHaveNoViolations()
})

it("o texto existe num único lugar do código (Q72)", () => {
  const found = sourceFiles(SRC)
    .filter((path) => readFileSync(path, "utf8").includes(PHRASE))
    .map((path) => relative(SRC, path))
  expect(found).toEqual(["components/surfaces/ConsentNotice/messages.ts"])
})
