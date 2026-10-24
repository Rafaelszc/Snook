import { describe, expect, it } from "vitest"

import { fakeBrowserEnv } from "./capture/fakes"
import { MESSAGES } from "./messages"
import { checkSupport, detectBrowser } from "./support"

describe("checkSupport", () => {
  it("bloqueia fora de contexto seguro (screen-recording 27)", () => {
    const result = checkSupport(fakeBrowserEnv({ secure: false }))
    expect(result).toEqual({ blocked: true, message: MESSAGES.insecure })
    expect(MESSAGES.insecure).toMatch(/HTTPS ou localhost/)
    expect(MESSAGES.insecure).toMatch(/perfil lan/)
    expect(MESSAGES.insecure).toMatch(/envio de arquivo/)
  })

  it("contexto inseguro vence a falta de API (screen-recording 27)", () => {
    const result = checkSupport(
      fakeBrowserEnv({ secure: false, displayMedia: false, webm: false })
    )
    expect(result).toEqual({ blocked: true, message: MESSAGES.insecure })
  })

  it("contexto seguro não bloqueia (screen-recording 28)", () => {
    expect(checkSupport(fakeBrowserEnv())).toEqual({ blocked: false })
  })

  it.each([
    { displayMedia: false, webm: true },
    { displayMedia: true, webm: false },
    { displayMedia: false, webm: false },
  ])("bloqueia sem as APIs: %o (screen-recording 22)", (apis) => {
    const result = checkSupport(fakeBrowserEnv(apis))
    expect(result).toEqual({ blocked: true, message: MESSAGES.unsupported })
    expect(MESSAGES.unsupported).toMatch(/Chrome ou Edge/)
    expect(MESSAGES.unsupported).toMatch(/envio de arquivo/)
  })

  it("avisa sem bloquear fora de Chrome e Edge (screen-recording 23)", () => {
    const result = checkSupport(fakeBrowserEnv({ browser: "other" }))
    expect(result).toEqual({ blocked: false, warning: MESSAGES.unofficial })
  })

  it("Edge não recebe aviso", () => {
    expect(checkSupport(fakeBrowserEnv({ browser: "edge" }))).toEqual({
      blocked: false,
    })
  })
})

describe("detectBrowser", () => {
  const CHROME =
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

  it.each([
    [CHROME, "chrome"],
    [`${CHROME} Edg/130.0.0.0`, "edge"],
    [`${CHROME} OPR/115.0.0.0`, "other"],
    [
      "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
      "other",
    ],
  ])("pelo user agent: %s", (ua, expected) => {
    expect(detectBrowser({ userAgent: ua })).toBe(expected)
  })

  it("prefere userAgentData quando existe", () => {
    expect(
      detectBrowser({
        userAgent: CHROME,
        userAgentData: { brands: [{ brand: "Microsoft Edge" }] },
      })
    ).toBe("edge")
    expect(
      detectBrowser({
        userAgent: CHROME,
        userAgentData: { brands: [{ brand: "Brave" }, { brand: "Chromium" }] },
      })
    ).toBe("other")
  })
})
