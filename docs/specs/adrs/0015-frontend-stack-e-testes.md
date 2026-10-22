# ADR-0015: Frontend com Vite, TanStack Query e testes com Vitest

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q10 da rodada de decisões do planner: Vite + React Router + TanStack Query + Vitest + React Testing Library + MSW. Recomendação aceita sem mudança.

## Contexto

- ADR-0001 (Aceita): React + TypeScript + shadcn/ui.
- Todos os PRDs deixavam aberto o framework de teste do frontend. Resolvido por este ADR.
- Gravação de tela usa seam com fakes de `getDisplayMedia`, `getUserMedia` e `MediaRecorder`.
- Status por polling (Q8).

## Opções consideradas

1. **Vite + React Router + TanStack Query (polling com `refetchInterval`) + Vitest + React Testing Library + MSW.**
   - Prós: shadcn/ui documenta Vite; Vitest compartilha config do Vite; MSW simula a API sem servidor.
   - Contras: jsdom não grava áudio real (checklist manual cobre).
2. **Next.js + Jest.**
   - Prós: ecossistema grande.
   - Contras: SSR sem uso num app local; servidor Node a mais.
3. **Vite + Playwright para tudo.**
   - Prós: navegador real.
   - Contras: lento; precisa de backend ou mocks pesados; ruim para TDD.

## Decisão

Opção 1.

- Polling a cada 3 s só nos status ativos (`pending`, `processing`, `generating`, `transcribed` com `participants_confirmed`). Variável `VITE_POLL_INTERVAL_MS`.
- Cliente API em `src/lib/api/` com `fetch`, `credentials: "same-origin"`, erro tipado com `code` e `message`.
- Gravação: `src/features/screen-recording/media.ts` define interfaces `DisplayCapture`, `MicCapture`, `Recorder`, `Clock`. Testes usam fakes.
- Mistura de fontes: Web Audio API (`AudioContext` + `MediaStreamAudioDestinationNode`). Codec `audio/webm;codecs=opus`, 64 kbps (cerca de 58 MB em 1h59m50s).
- Ordem dos pedidos: tela primeiro (precisa de gesto do usuário), depois microfone.
- Playwright fica fora da primeira versão. Critérios de navegador real seguem o checklist manual do PRD.

## Consequências

- Sem SSR. Build estático servido por nginx (ADR-0016).
- Dependências novas aprovadas com este ADR: `vite`, `react-router`, `@tanstack/react-query`, `vitest`, `@testing-library/react`, `msw`.
- Dependência de teste `vitest-axe` (axe-core no Vitest; ou equivalente com o mesmo motor `axe-core`), exigida pela checagem de contraste e rótulo do ADR-0022. Fonte: correções da revisão do spec-reviewer aceitas pelo usuário em 2026-10-22. Só `devDependencies`; troca por outra biblioteca passa por "Ask First".
