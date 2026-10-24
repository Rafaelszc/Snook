import type {
  Browser,
  BrowserEnv,
  DisplayCapture,
  MicCapture,
} from "./interfaces"

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

function fakeTrack(kind: "audio" | "video"): MediaStreamTrack {
  const track = {
    kind,
    readyState: "live" as MediaStreamTrackState,
    stop() {
      track.readyState = "ended"
    },
  }
  return track as unknown as MediaStreamTrack
}

// jsdom não tem MediaStream. `video` simula a trilha de vídeo que `getDisplayMedia` sempre traz.
export function fakeStream({
  audio,
  video = false,
}: {
  audio: boolean
  video?: boolean
}): MediaStream {
  const tracks = [
    ...(audio ? [fakeTrack("audio")] : []),
    ...(video ? [fakeTrack("video")] : []),
  ]
  return {
    getTracks: () => tracks,
    getAudioTracks: () => tracks.filter((t) => t.kind === "audio"),
    getVideoTracks: () => tracks.filter((t) => t.kind === "video"),
  } as unknown as MediaStream
}

// Resolve com o stream ou rejeita com o erro, como o pedido real.
export function fakeCapture(
  result: MediaStream | DOMException | Error,
  onRequest?: () => void
): DisplayCapture & MicCapture {
  return {
    request() {
      onRequest?.()
      // DOMException do jsdom não herda de Error.
      return "getTracks" in result
        ? Promise.resolve(result)
        : Promise.reject(result)
    },
  }
}
