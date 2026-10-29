# ADR-0022: Direção visual e design system do frontend

- Status: Aceita (direção visual e restrições); detalhes de implementação abaixo seguem a direção e podem ser ajustados nas tarefas sem novo ADR.
- Substituído em parte pelo [ADR-0024](0024-direcao-visual-ata.md) (direção "Ata", 2026-10-28, Q74), nas seções:
  - Tokens: paleta, raio e sombra. A troca manual de tema segue, com controle visível e sem atalho de tecla `d`;
  - Tipografia: família única vira três (Source Serif 4, Geist, Geist Mono);
  - Vidro: só no painel flutuante da gravação; barra, diálogos, confirmações, toasts e card de auth opacos;
  - Mouse-tracking: só na área de upload, só na borda; login e cadastro sem spotlight;
  - Movimento: skeleton com respiração de opacidade em laço passa a contar como indicador de progresso.
- Segue valendo: restrições do Contexto, regra de 4,5:1 e 3:1, escala tipográfica, pesos, mono tabular, receita e fallbacks do vidro, tokens e curva de movimento, só `transform` e `opacity`, ativação do mouse-tracking, acessibilidade e responsividade.
- Data: 2026-10-22
- Fonte: diretriz do usuário para o frontend, repassada ao planner em 2026-10-22.

## Contexto

- ADR-0001 (Aceita): React + TypeScript + shadcn/ui.
- Diretriz do usuário: visual minimalista, alto contraste, hierarquia tipográfica bem estruturada, animações suaves, efeito de vidro (glassmorphism) e efeito de rastreio do mouse (mouse-tracking) só onde agrega, sem exagero.
- Restrições da diretriz:
  - respeitar `prefers-reduced-motion`;
  - contraste WCAG AA mesmo sobre o vidro, com fallback opaco para `backdrop-filter`;
  - mouse-tracking desligado em telas de toque e com movimento reduzido;
  - custo de performance dentro dos NFRs do `01-prd.md` (NFRs de frontend definidos no ADR-0023, Aceita; inclusão no `01-prd.md` aprovada pelo usuário em 2026-10-22).
- CSP `default-src 'self'` (SEC-13) e uso offline pedem fontes e ícones locais.
- Telas densas: Transcrição de até 2 h, tela de divisão, revisão do backlog.

## Opções consideradas

1. **Tokens em CSS variables sobre shadcn/ui + Tailwind; vidro só em superfícies flutuantes; movimento só em CSS (transições e `data-state` do Radix); mouse-tracking por CSS variables atualizadas em `requestAnimationFrame`, em dois lugares.**
   - Prós: zero dependência nova; tema único para claro e escuro; efeito barato; fácil de desligar por media query.
   - Contras: coreografia complexa de animação fica limitada.
2. **Mesmo, com biblioteca de animação (Motion, ex-Framer Motion).**
   - Prós: animação de layout e de saída mais rica.
   - Contras: cerca de 30 a 50 KB gzip a mais; dependência nova ("Ask First"); tentação de exagero.
3. **Vidro e mouse-tracking em toda a UI.**
   - Contras: contraria "só onde agregar"; leitura pior em telas densas; custo de GPU em listas longas.

## Decisão

Opção 1.

### Tokens

> Paleta, raio e sombra substituídos pelo ADR-0024 ("Cor", "Forma", "Profundidade"). Controle de tema: ADR-0024, "Tema".

- Arquivo `frontend/src/styles/tokens.css`. Temas claro e escuro por `prefers-color-scheme`, com troca manual guardada em `localStorage` (preferência visual, não segredo).
- Paleta neutra de alto contraste e uma cor de destaque. Cores de estado (`pending`, `processing`, `failed`, `done`) sempre com texto ou ícone, nunca só cor.
- Texto normal com contraste mínimo de 4,5:1; texto grande e componentes de UI (bordas de campo, foco, ícones) com 3:1 (WCAG 2.2 AA, 1.4.3 e 1.4.11).
- Raio, espaçamento (escala de 4 px) e sombras como tokens. Componentes shadcn leem só tokens.

### Tipografia

> Família substituída pelo ADR-0024 ("Tipografia"): Source Serif 4, Geist e Geist Mono. Escala, alturas de linha, pesos e limite de tamanhos seguem.

- Uma família sans variável, servida pelo próprio app (sem CDN; CSP e offline). Candidata: Inter ou Geist; escolha na Task de design system.
- Escala fixa: 12, 14, 16, 20, 24, 32, 40 px; corpo em 16 px; altura de linha 1,5 no corpo e 1,2 nos títulos.
- Pesos: 400 corpo, 500 rótulos, 600 títulos. No máximo três tamanhos por tela.
- Fonte mono com algarismos tabulares para `US-id`, instantes `hh:mm:ss`, estimativas de tokens e cronômetro da gravação.

### Vidro (glassmorphism)

> Onde usar substituído pelo ADR-0024 ("Vidro"): só no painel flutuante da gravação. Receita, limite e fallbacks abaixo seguem.

- Só em superfícies flutuantes: barra de navegação fixa, diálogos e confirmações, painel flutuante da gravação, toasts.
- Nunca em listas, tabelas, Transcrição, tela de divisão e cards do backlog.
- No máximo 3 elementos com `backdrop-filter` visíveis ao mesmo tempo.
- Receita: `backdrop-filter: blur(12px) saturate(140%)` com fundo de opacidade suficiente para o texto manter 4,5:1 sobre o pior fundo possível (conferido com o fundo mais claro e o mais escuro do tema).
- Fallback opaco (mesma cor sem transparência) em:
  - `@supports not (backdrop-filter: blur(1px))`;
  - `@media (prefers-reduced-transparency: reduce)`;
  - `@media (forced-colors: active)`, com cores do sistema.

### Movimento

> Exceção do ADR-0024 ("Movimento"): skeleton com respiração lenta de opacidade conta como indicador de progresso. `transition-colors` e `transition: all` proibidos.

- Só `transform` e `opacity`. Duração de 120 a 240 ms. Curva padrão `cubic-bezier(0.2, 0, 0, 1)`. Tokens `--motion-fast`, `--motion-base`, `--motion-slow`.
- Usos: entrada e saída de diálogo e toast, troca de status na lista, abrir e fechar Epic, feedback de corte na divisão, pulso discreto do indicador de gravação.
- `@media (prefers-reduced-motion: reduce)`: transições viram troca instantânea (ou opacidade de até 100 ms); pulso de gravação vira indicador fixo; nenhum movimento automático.
- Sem animação em loop, exceto indicador de progresso e de gravação.

### Mouse-tracking

> Onde usar substituído pelo ADR-0024 ("Mouse-tracking"): só na borda da área de upload. Implementação e ativação abaixo seguem.

- Só em dois lugares: realce do card de login e cadastro, e realce da área de upload (soltar arquivo).
- Implementação: hook `usePointerSpotlight` grava `--pointer-x` e `--pointer-y` no elemento via `style.setProperty`, num `requestAnimationFrame` por quadro. Sem estado React por movimento. Nomes iguais aos de `styles/spotlight.css` (linhas 2 e 17).
- Liga só com `matchMedia("(hover: hover) and (pointer: fine)")` verdadeiro e `prefers-reduced-motion` diferente de `reduce`. Fora disso, nenhum listener é registrado.
- Efeito é decorativo: sem informação nova, sem mudar foco, sem afetar contraste do texto.

### Acessibilidade e responsividade

- WCAG 2.2 AA em todas as telas.
- Foco visível com anel de 2 px e contraste de 3:1. Anel opaco, sem alfa (ADR-0024, "Foco").
- Toda ação por teclado, inclusive mover cortes na divisão e tocar amostra.
- Mudança de status anunciada por `aria-live="polite"`.
- Alvos de clique de 24 x 24 px no mínimo.
- Layout funciona de 360 px a 1920 px de largura. Prioridade desktop (gravação em Chrome e Edge desktop).

## Consequências

- Sem dependência nova de animação. Pedir uma depois passa por "Ask First".
- Testes do frontend cobrem: hook de spotlight não registra listener com movimento reduzido nem em toque; classe de fallback opaco quando `backdrop-filter` não é suportado.
- Contraste conferido por ferramenta (axe no Vitest e checagem manual) em cada checkpoint de tela.
- Orçamento de performance: ADR-0023.
