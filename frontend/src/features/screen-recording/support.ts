import type { Browser, BrowserEnv } from "./capture/interfaces"
import { MESSAGES } from "./messages"

// ADR-0015: só áudio, opus em webm.
export const RECORDING_MIME = "audio/webm;codecs=opus"

export type Support =
  { blocked: true; message: string } | { blocked: false; warning?: string }

// Ordem fixa: contexto seguro (`screen-recording` 27) antes das APIs (22), aviso por último (23).
export function checkSupport(env: BrowserEnv): Support {
  if (!env.secureContext.isSecure()) {
    return { blocked: true, message: MESSAGES.insecure }
  }
  if (!env.hasDisplayMedia() || !env.supportsWebm()) {
    return { blocked: true, message: MESSAGES.unsupported }
  }
  if (env.browser() === "other" || env.browser() === "firefox") {
    return { blocked: false, warning: MESSAGES.unofficial }
  }
  return { blocked: false }
}

interface NavigatorLike {
  userAgent: string
  userAgentData?: { brands: { brand: string }[] }
}

export function detectBrowser(nav: NavigatorLike): Browser {
  const brands = nav.userAgentData?.brands.map((b) => b.brand)
  if (brands) {
    if (brands.includes("Microsoft Edge")) return "edge"
    if (brands.includes("Google Chrome")) return "chrome"
    return "other"
  }
  const ua = nav.userAgent
  if (/\bFirefox\//.test(ua)) return "firefox"
  if (/\bEdg\//.test(ua)) return "edge"
  if (/\bChrome\//.test(ua) && !/\b(OPR|SamsungBrowser|YaBrowser)\//.test(ua)) {
    return "chrome"
  }
  return "other"
}

export function browserEnv(): BrowserEnv {
  return {
    secureContext: { isSecure: () => window.isSecureContext },
    hasDisplayMedia: () =>
      typeof navigator.mediaDevices?.getDisplayMedia === "function",
    supportsWebm: () =>
      typeof MediaRecorder !== "undefined" &&
      MediaRecorder.isTypeSupported(RECORDING_MIME),
    browser: () => detectBrowser(navigator as NavigatorLike),
  }
}
