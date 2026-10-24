import type { Browser, BrowserEnv } from "./interfaces"

export function fakeBrowserEnv({
  secure = true,
  displayMedia = true,
  webm = true,
  browser = "chrome",
}: {
  secure?: boolean
  displayMedia?: boolean
  webm?: boolean
  browser?: Browser
} = {}): BrowserEnv {
  return {
    secureContext: { isSecure: () => secure },
    hasDisplayMedia: () => displayMedia,
    supportsWebm: () => webm,
    browser: () => browser,
  }
}
