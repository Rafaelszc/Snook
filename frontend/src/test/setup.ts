import "@testing-library/jest-dom/vitest"

import { cleanup } from "@testing-library/react"
import { afterAll, afterEach, beforeAll, expect } from "vitest"
import * as axeMatchers from "vitest-axe/matchers"

import { server } from "./server"

expect.extend(axeMatchers)

// Sem rede: requisição sem handler falha o teste.
beforeAll(() => server.listen({ onUnhandledFrame: "error" }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
})
afterAll(() => server.close())
