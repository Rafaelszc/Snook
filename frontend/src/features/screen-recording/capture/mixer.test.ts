import { describe, expect, it } from "vitest"

import { fakeAudioContext, fakeMediaRecorder, fakeStream } from "./fakes"
import { mixSources } from "./mixer"
import {
  AUDIO_BITS_PER_SECOND,
  MAX_RECORDING_SECONDS,
  createRecorder,
  projectedBytes,
} from "./recorder"

// ADR-0018: 500 MiB.
const MAX_UPLOAD_BYTES = 524_288_000

describe("mixSources", () => {
  it("liga tela e microfone num destino único (screen-recording 3)", () => {
    const ctx = fakeAudioContext()
    const display = fakeStream({ audio: true, video: true })
    const mic = fakeStream({ audio: true })
    const mix = mixSources({ display, mic }, () => ctx.context)

    expect(ctx.connected).toEqual([display, mic])
    expect(mix.stream).toBe(ctx.destination.stream)
  })

  it("trilha única, só de áudio (screen-recording 9)", () => {
    const ctx = fakeAudioContext()
    const mix = mixSources(
      { display: fakeStream({ audio: true, video: true }) },
      () => ctx.context
    )
    expect(mix.stream.getAudioTracks()).toHaveLength(1)
    expect(mix.stream.getVideoTracks()).toHaveLength(0)
  })

  it("close fecha o AudioContext", async () => {
    const ctx = fakeAudioContext()
    const mix = mixSources(
      { mic: fakeStream({ audio: true }) },
      () => ctx.context
    )
    await mix.close()
    expect(ctx.closed).toBe(true)
  })
})

describe("createRecorder", () => {
  it("grava opus em webm a 64 kbps (ADR-0015)", async () => {
    const fake = fakeMediaRecorder()
    const recorder = createRecorder(fake.ctor)
    const stream = fakeStream({ audio: true })
    recorder.start(stream)

    expect(fake.instances[0]?.stream).toBe(stream)
    expect(fake.instances[0]?.options).toEqual({
      mimeType: "audio/webm;codecs=opus",
      audioBitsPerSecond: 64_000,
    })

    fake.instances[0]?.emit(new Blob(["a"]))
    fake.instances[0]?.emit(new Blob(["b"]))
    const blob = await recorder.stop()
    expect(blob.type).toBe("audio/webm")
    expect(await blob.text()).toBe("ab")
  })
})

it("1h59m50s a 64 kbps fica abaixo de 500 MiB (screen-recording 24)", () => {
  expect(AUDIO_BITS_PER_SECOND).toBe(64_000)
  expect(MAX_RECORDING_SECONDS).toBe(7190)
  expect(projectedBytes(MAX_RECORDING_SECONDS)).toBeLessThan(MAX_UPLOAD_BYTES)
})
