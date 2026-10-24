import type { DisplayCapture, MicCapture } from "./interfaces"

// Chrome exige `video` em `getDisplayMedia`; a trilha de vídeo nunca é gravada (`screen-recording` 9).
export const browserDisplay: DisplayCapture = {
  request: () =>
    navigator.mediaDevices.getDisplayMedia({ video: true, audio: true }),
}

export const browserMic: MicCapture = {
  request: () => navigator.mediaDevices.getUserMedia({ audio: true }),
}
