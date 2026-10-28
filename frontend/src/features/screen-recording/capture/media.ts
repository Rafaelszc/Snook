import type { Clock, DisplayCapture, MicCapture } from "./interfaces"

// Chrome exige `video` em `getDisplayMedia`; a trilha de vídeo nunca é gravada (`screen-recording` 9).
// Só aba traz som em todo sistema; janela nunca traz, tela inteira só no Windows e ChromeOS.
// Por isso o seletor abre em "Aba" e esconde a própria aba do Snook.
// `lib.dom` do TS ainda não tipa as dicas do Chrome; navegador que não conhece ignora.
const DISPLAY_OPTIONS: DisplayMediaStreamOptions & {
  selfBrowserSurface: "exclude"
  systemAudio: "include"
} = {
  video: { displaySurface: "browser" },
  audio: true,
  selfBrowserSurface: "exclude",
  systemAudio: "include",
}

export const browserDisplay: DisplayCapture = {
  request: () => navigator.mediaDevices.getDisplayMedia(DISPLAY_OPTIONS),
}

export const browserMic: MicCapture = {
  request: () => navigator.mediaDevices.getUserMedia({ audio: true }),
}

export const systemClock: Clock = { now: () => Date.now() }
