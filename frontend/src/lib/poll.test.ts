import { afterEach, expect, it, vi } from "vitest"

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

it("usa 3000 ms por padrão", async () => {
  const { POLL_INTERVAL_MS } = await import("./poll")
  expect(POLL_INTERVAL_MS).toBe(3000)
})

it("lê VITE_POLL_INTERVAL_MS", async () => {
  vi.stubEnv("VITE_POLL_INTERVAL_MS", "500")
  const { POLL_INTERVAL_MS } = await import("./poll")
  expect(POLL_INTERVAL_MS).toBe(500)
})
