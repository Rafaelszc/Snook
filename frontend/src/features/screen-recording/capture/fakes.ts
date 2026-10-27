import type {
  Browser,
  BrowserEnv,
  DisplayCapture,
  MicCapture,
} from "./interfaces"
import type { AudioGraph } from "./mixer"
import type { MediaRecorderCtor, MediaRecorderLike } from "./recorder"

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

// `stop()` não dispara `ended`, como no navegador; `endTrack` simula o fim pela barra do navegador.
function fakeTrack(kind: "audio" | "video"): MediaStreamTrack {
  const track = Object.assign(new EventTarget(), {
    kind,
    readyState: "live" as MediaStreamTrackState,
    stop() {
      track.readyState = "ended"
    },
  })
  return track as unknown as MediaStreamTrack
}

export function endTrack(track: MediaStreamTrack) {
  ;(track as { readyState: MediaStreamTrackState }).readyState = "ended"
  track.dispatchEvent(new Event("ended"))
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

export function fakeAudioContext() {
  const connected: MediaStream[] = []
  const destination = { stream: fakeStream({ audio: true }) }
  const fake = {
    connected,
    destination,
    closed: false,
    context: {
      createMediaStreamDestination: () => destination,
      createMediaStreamSource: (stream: MediaStream) => ({
        connect: (node: unknown) => {
          if (node === destination) connected.push(stream)
        },
      }),
      close: () => {
        fake.closed = true
        return Promise.resolve()
      },
    } as unknown as AudioGraph,
  }
  return fake
}

class FakeMediaRecorder implements MediaRecorderLike {
  ondataavailable: ((event: BlobEvent) => void) | null = null
  onstop: ((event: Event) => void) | null = null
  readonly stream: MediaStream
  readonly options: MediaRecorderOptions
  constructor(stream: MediaStream, options: MediaRecorderOptions) {
    this.stream = stream
    this.options = options
  }
  start() {}
  stop() {
    this.onstop?.(new Event("stop"))
  }
  emit(data: Blob) {
    this.ondataavailable?.({ data } as BlobEvent)
  }
}

export function fakeMediaRecorder() {
  const instances: FakeMediaRecorder[] = []
  const ctor = class extends FakeMediaRecorder {
    constructor(stream: MediaStream, options: MediaRecorderOptions) {
      super(stream, options)
      instances.push(this)
    }
  }
  return { ctor: ctor satisfies MediaRecorderCtor, instances }
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
