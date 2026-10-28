// Seams do navegador (ADR-0015). Testes trocam por fakes de `./fakes`.

// `firefox` cobre derivados (Zen, LibreWolf): `getDisplayMedia` sem áudio.
export type Browser = "chrome" | "edge" | "firefox" | "other"

export interface DisplayCapture {
  // `getDisplayMedia` com áudio; precisa de gesto do usuário, vem antes do microfone.
  request(): Promise<MediaStream>
}

export interface MicCapture {
  request(): Promise<MediaStream>
}

export interface Recorder {
  start(stream: MediaStream): void
  stop(): Promise<Blob>
}

export interface Clock {
  now(): number
}

export interface SecureContext {
  isSecure(): boolean
}

// O que a checagem de suporte lê do navegador.
export interface BrowserEnv {
  secureContext: SecureContext
  hasDisplayMedia(): boolean
  supportsWebm(): boolean
  browser(): Browser
}
