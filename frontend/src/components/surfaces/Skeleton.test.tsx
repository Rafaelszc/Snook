import { render, screen } from "@testing-library/react"
import { axe } from "vitest-axe"
import { afterEach, describe, expect, it, vi } from "vitest"

import { REDUCED_MOTION_QUERY } from "@/lib/ui/media"
import { stubMatchMedia } from "@/lib/ui/matchMediaStub"

import { Skeleton, SkeletonGroup } from "./Skeleton"

afterEach(() => vi.unstubAllGlobals())

function renderGroup() {
  return render(
    <SkeletonGroup label="Carregando…">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-4 w-48" />
    </SkeletonGroup>
  )
}

describe("Skeleton", () => {
  it("usa --sunken e --r-4 e respira sem movimento reduzido", () => {
    stubMatchMedia({ [REDUCED_MOTION_QUERY]: false })
    const { container } = renderGroup()
    const blocks = container.querySelectorAll('[data-slot="skeleton"]')
    expect(blocks).toHaveLength(2)
    for (const b of blocks) {
      expect(b).toHaveClass("bg-sunken", "rounded-sm", "motion-breathe")
      expect(b).toHaveAttribute("aria-hidden", "true")
    }
  })

  it("fica parado com prefers-reduced-motion", () => {
    stubMatchMedia({ [REDUCED_MOTION_QUERY]: true })
    const { container } = renderGroup()
    for (const b of container.querySelectorAll('[data-slot="skeleton"]')) {
      expect(b).not.toHaveClass("motion-breathe")
    }
  })

  it("o contêiner anuncia o carregamento", () => {
    stubMatchMedia({ [REDUCED_MOTION_QUERY]: false })
    renderGroup()
    const status = screen.getByRole("status")
    expect(status).toHaveAttribute("aria-busy", "true")
    expect(status).toHaveTextContent("Carregando…")
  })

  it("não tem violação de acessibilidade", async () => {
    stubMatchMedia({ [REDUCED_MOTION_QUERY]: false })
    const { container } = renderGroup()
    expect(await axe(container)).toHaveNoViolations()
  })
})
