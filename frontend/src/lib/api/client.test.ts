import { http, HttpResponse } from "msw"
import { afterEach, expect, it, vi } from "vitest"

import { server } from "@/test/server"
import { api } from "./client"
import { ApiError, isApiError } from "./errors"

afterEach(() => vi.restoreAllMocks())

it("converte o corpo de erro em ApiError tipado", async () => {
  server.use(
    http.put("/api/meetings/1", () =>
      HttpResponse.json(
        {
          error: {
            code: "validation_error",
            message: "Dados inválidos.",
            fields: { title: "Título não pode ser vazio." },
          },
        },
        { status: 422 }
      )
    )
  )
  const error = await api.put("/meetings/1", { title: "" }).catch((e) => e)
  expect(isApiError(error)).toBe(true)
  expect(error).toBeInstanceOf(ApiError)
  expect(error).toMatchObject({
    status: 422,
    code: "validation_error",
    message: "Dados inválidos.",
    fields: { title: "Título não pode ser vazio." },
  })
})

it("erro sem corpo do contrato vira unknown_error", async () => {
  server.use(
    http.get("/api/boom", () => new HttpResponse("<html>", { status: 502 }))
  )
  const error = await api.get("/boom").catch((e) => e)
  expect(error).toMatchObject({
    status: 502,
    code: "unknown_error",
    fields: {},
  })
})

it("falha de rede vira network_error", async () => {
  server.use(http.get("/api/down", () => HttpResponse.error()))
  const error = await api.get("/down").catch((e) => e)
  expect(error).toMatchObject({ status: 0, code: "network_error" })
})

it("envia JSON com cookie de mesma origem e lê 204", async () => {
  let seen: Request | undefined
  server.use(
    http.post("/api/auth/logout", ({ request }) => {
      seen = request
      return new HttpResponse(null, { status: 204 })
    })
  )
  await expect(api.post("/auth/logout")).resolves.toBeUndefined()
  expect(seen?.credentials).toBe("same-origin")

  server.use(
    http.post("/api/auth/login", async ({ request }) => {
      expect(request.headers.get("content-type")).toBe("application/json")
      return HttpResponse.json(await request.json())
    })
  )
  await expect(api.post("/auth/login", { username: "a" })).resolves.toEqual({
    username: "a",
  })
})

it("nunca grava em localStorage nem sessionStorage", async () => {
  const local = vi.spyOn(Storage.prototype, "setItem")
  server.use(
    http.post("/api/auth/login", () =>
      HttpResponse.json(
        { token: "segredo" },
        { headers: { "Set-Cookie": "s=1" } }
      )
    ),
    http.get("/api/x", () =>
      HttpResponse.json(
        { error: { code: "not_authenticated", message: "x" } },
        { status: 401 }
      )
    )
  )
  await api.post("/auth/login", { username: "a", password: "b" })
  await api.get("/x").catch(() => undefined)
  expect(local).not.toHaveBeenCalled()
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})
