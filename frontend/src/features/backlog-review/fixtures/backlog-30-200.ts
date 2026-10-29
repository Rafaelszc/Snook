import type { Backlog, Epic, UserStory } from "../api"

// NFR-04: 30 Epics e 200 US para medir INP na tela de revisão.
export function bigBacklog(epicCount = 30, storyCount = 200): Backlog {
  const epics: Epic[] = Array.from({ length: epicCount }, (_, i) => ({
    id: i + 1,
    name: `Epic ${i + 1}: módulo ${["Cadastro", "Vendas", "Relatórios"][i % 3]}`,
    user_stories: [],
  }))
  for (let n = 1; n <= storyCount; n++) {
    const story: UserStory = {
      id: n,
      us_id: `US-${String(n).padStart(n >= 100 ? 3 : 2, "0")}`,
      name: `Registrar pedido ${n}`,
      as_a: "atendente da loja",
      i_want: `registrar o pedido ${n} com itens, desconto e forma de pagamento`,
      so_that: "o estoque e o financeiro fiquem atualizados no mesmo dia",
      priority: (["Low", "Medium", "High"] as const)[n % 3],
      story_points: [1, 2, 3, 5, 8, 13][n % 6],
      requested_by:
        n % 4 === 0
          ? null
          : { id: (n % 3) + 1, name: ["Ana", "Bruno", "Carla"][n % 3] },
      requested_at:
        n % 5 === 0 ? null : `00:${String(n % 60).padStart(2, "0")}:15`,
      acceptance_criteria: [
        {
          id: n * 10,
          given: "um pedido aberto",
          when: "confirmo o pagamento",
          then: "o pedido fica pago",
        },
        {
          id: n * 10 + 1,
          given: "um item sem estoque",
          when: "tento confirmar",
          then: "vejo o aviso de falta",
        },
      ],
    }
    epics[(n - 1) % epicCount].user_stories.push(story)
  }
  return { read_only: false, last_generation_failed: false, epics }
}
