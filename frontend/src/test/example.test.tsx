import { useQuery } from "@tanstack/react-query"
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { expect, it } from "vitest"
import { axe } from "vitest-axe"

import { server } from "./server"
import { renderWithProviders } from "./render"

function Health() {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: () => fetch("/api/health").then((r) => r.json()),
  })
  return <p>{data ? `status: ${data.status}` : "carregando"}</p>
}

it("renderiza, mocka rota com MSW e passa vitest-axe", async () => {
  server.use(http.get("/api/health", () => HttpResponse.json({ status: "ok" })))
  const { container } = renderWithProviders(<Health />)
  expect(await screen.findByText("status: ok")).toBeInTheDocument()
  expect(await axe(container)).toHaveNoViolations()
})
