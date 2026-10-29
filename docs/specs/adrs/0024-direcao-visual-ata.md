# ADR-0024: Direção visual "Ata"

- Status: Aceita
- Data: 2026-10-28
- Fonte: decisão Q74 de `docs/specs/00-overview.md` (diretriz do usuário de 2026-10-28, redesign visual com identidade própria). Aprovou: restringir vidro e mouse-tracking, tipografia serif + sans + mono, um acento petróleo. Amostras aprovadas antes deste ADR. Correções da revisão do spec-reviewer e rodada Q1 a Q7 do planner aceitas pelo usuário em 2026-10-28 ("aceito tudo"). Segunda revisão do spec-reviewer: Q1 (opção C, troca só das classes de cor na Task 52) e Q2 (opção A, spotlight só na borda) aceitas pelo usuário em 2026-10-28 ("Aceito").
- Substitui em parte:
  - [ADR-0022](0022-direcao-visual-e-design-system.md), seções:
    - Tokens: paleta, raio e sombra (a troca manual de tema segue, com controle visível; ver "Tema");
    - Tipografia: família única vira três famílias;
    - Vidro: só no painel da gravação;
    - Mouse-tracking: só na área de upload;
    - Movimento: skeleton com respiração em laço entra como indicador de progresso.
  - [ADR-0023](0023-orcamento-de-performance-do-frontend.md), item "Fonte variável única, subset latino" da Decisão: vira três famílias, quatro arquivos novos, preload de dois.
- Segue valendo do ADR-0022: tokens de movimento e curva, uso só de `transform` e `opacity`, acessibilidade, responsividade, receita e fallbacks do `GlassPanel`, regras de ativação do `usePointerSpotlight`.

## Contexto

- Auditoria do frontend em 2026-10-28:
  - paleta igual ao neutro padrão do shadcn, destaque índigo (`oklch(0.48 0.2 264)`); sem identidade;
  - Geist sozinha, mono do sistema; conteúdo e controle com a mesma voz;
  - shell sem estado ativo na nav, sem marca, largura máxima diferente em cada página;
  - excesso de caixa: `rounded-xl` 31 vezes, `rounded-lg` 30; backlog vira pilha de cards;
  - alerta de erro copiado inline 13 vezes; skeleton copiado em 7 páginas;
  - `text-[0.8rem]` fora da escala; tokens `chart-*` e `sidebar-*` sem uso.
- Nova diretriz: minimalismo funcional, sem visual de template SaaS; sem gradiente, vidro, blur, sombra forte ou raio grande por padrão, só com justificativa.
- Referências estudadas pelo CSS publicado: claude.com (trio serif/sans/mono, neutros quentes, um acento, sombra quase nula), antigravity.google (tinta quase preta, raio pequeno em controle, mono técnica), zen-browser.app (chrome baixo, conteúdo primeiro). Usadas como princípio, sem copiar cor, fonte ou layout.
- Snook produz ata e backlog. Telas centrais são leitura de texto longo (Transcrição, US).

## Opções consideradas

1. **"Ata": papel, tinta, linha fina, um acento. Serif para conteúdo, sans para controle, mono para dado. Vidro só no painel de gravação.**
   - Prós: identidade ligada ao domínio; menos caixa, hierarquia por régua e espaço; zero dependência npm nova.
   - Contras: quatro arquivos de fonte a mais (peso de rede); mexe em critérios já entregues (diálogos com vidro, spotlight no login).
2. **Manter ADR-0022 e só trocar a cor de destaque.**
   - Prós: mudança mínima.
   - Contras: não resolve caixa demais, voz única, shell fraco.
3. **Visual escuro único, denso, estilo IDE.**
   - Prós: forte para telas densas.
   - Contras: pior para leitura longa da Transcrição; foge do pedido de minimalismo calmo.

## Decisão

Opção 1.

### Princípios

- Linha, não caixa: hierarquia por régua e espaço. Card só no que flutua (diálogo, popover, painel de gravação).
- Exceção explícita: card de login e cadastro. Fica opaco (`--surface`), com régua `--hairline`, sem sombra (Q3). Motivo: tela sem shell; o card agrupa o formulário.
- Três vozes: serif no conteúdo da reunião, sans nos controles, mono em ids, instantes e tokens.
- Um destaque: `--signal` (petróleo) marca foco, item ativo, progresso e no máximo uma ação de avanço por tela.
- Calma: chrome baixo, conteúdo primeiro.

### Cor

- Camada semântica nova em `tokens.css`. Nomes do shadcn viram apelidos dela (tabela "Apelidos"), para os componentes shadcn seguirem lendo só tokens.
- Remover `--chart-*` e `--sidebar-*` em `tokens.css`, os `--color-chart-*` e `--color-sidebar-*` do `@theme` em `index.css` (linhas 43 a 55) e o par `--sidebar-foreground` de `tokens.test.ts` (linha 52).
- Remover `--highlight`, `--highlight-foreground`, `--status-*`, `--elevation-1`, `--elevation-2` e `--radius`. Destino na tabela "Apelidos", em "Estados" e em "Classes de cor a trocar".
- Neutros: papel com viés quente (hue 85), tinta com viés frio (hue 220).

#### Tokens

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--canvas` | `oklch(0.985 0.004 85)` | `oklch(0.175 0.009 220)` | fundo da página |
| `--surface` | `oklch(0.998 0.002 85)` | `oklch(0.215 0.011 220)` | diálogo, popover, campo, card de auth |
| `--sunken` | `oklch(0.963 0.006 85)` | `oklch(0.15 0.008 220)` | hover de linha, skeleton, tag, `Notice` de consentimento |
| `--hairline` | `oklch(0.9 0.007 85)` | `oklch(0.3 0.012 220)` | divisor (decorativo) |
| `--ink` | `oklch(0.22 0.015 220)` | `oklch(0.94 0.006 85)` | texto, ação primária |
| `--ink-muted` | `oklch(0.5 0.014 220)` | `oklch(0.72 0.012 220)` | texto de apoio |
| `--input` | `oklch(0.62 0.012 220)` | `oklch(0.56 0.012 220)` | borda de campo e de botão secundário |
| `--signal` | `oklch(0.47 0.08 210)` | `oklch(0.76 0.09 205)` | foco, ativo, progresso, ação de avanço |
| `--signal-ink` | `oklch(0.985 0.004 85)` | `oklch(0.175 0.009 220)` | texto sobre `--signal` |
| `--signal-soft` | `oklch(0.95 0.022 210)` | `oklch(0.27 0.035 210)` | seleção, `Notice` info |
| `--done` | `oklch(0.47 0.1 150)` | `oklch(0.77 0.12 150)` | Concluída, sucesso |
| `--warn` | `oklch(0.52 0.11 65)` | `oklch(0.8 0.12 75)` | Precisa dividir, `Notice` warn |
| `--warn-soft` | `oklch(0.96 0.03 75)` | `oklch(0.26 0.035 70)` | fundo do `Notice` warn (valor proposto) |
| `--failed` | `oklch(0.52 0.18 28)` | `oklch(0.72 0.15 25)` | Falhou, excluir, erro |
| `--failed-soft` | `oklch(0.96 0.025 28)` | `oklch(0.26 0.04 25)` | fundo do `Notice` error (valor proposto) |
| `--scrim` | `oklch(0.22 0.015 220 / 40%)` | `oklch(0.1 0.008 220 / 50%)` | fundo atrás de diálogo; cor translúcida, sem blur |
| `--overlay-shadow` | `0 1px 2px oklch(0 0 0 / 6%), 0 12px 32px oklch(0 0 0 / 10%)` | `0 1px 2px oklch(0 0 0 / 40%), 0 12px 32px oklch(0 0 0 / 45%)` | única elevação: diálogo, popover, painel de gravação |
| `--ring` | `var(--signal)` | `var(--signal)` | anel de foco, sem alfa |

- "Opaco" neste ADR quer dizer sem `backdrop-filter`. `--scrim` é cor translúcida e não conta como vidro.

#### Apelidos (shadcn para Ata)

| Apelido shadcn | Token Ata | Observação |
|---|---|---|
| `--background` | `--canvas` | |
| `--foreground` | `--ink` | |
| `--card`, `--card-foreground` | `--surface`, `--ink` | |
| `--popover`, `--popover-foreground` | `--surface`, `--ink` | |
| `--primary` | `--ink` | botão `primary` em tinta |
| `--primary-foreground` | `--canvas` | texto do `primary` |
| `--secondary`, `--secondary-foreground` | `--sunken`, `--ink` | |
| `--muted`, `--muted-foreground` | `--sunken`, `--ink-muted` | |
| `--accent`, `--accent-foreground` | `--sunken`, `--ink` | fundo de hover do shadcn (Q2); não é a cor de destaque |
| `--destructive` | `--failed` | |
| `--border` | `--hairline` | |
| `--input` | `--input` | mesmo nome; valor da tabela "Tokens" |
| `--ring` | `--signal` | opaco |
| `--highlight` | removido | destino por uso em "Classes de cor a trocar" |
| `--highlight-foreground` | removido | destino por uso em "Classes de cor a trocar" |

#### Estados

| Estado | Ícone (atual) | Cor do ícone | Cor do rótulo | Token antigo |
|---|---|---|---|---|
| `pending` | `Clock` | `--ink-muted` | `--ink` | `--status-pending` removido |
| `processing` | `Loader` | `--signal` | `--ink` | `--status-processing` removido |
| `transcribed` | `CheckCheck` | `--ink` | `--ink` | era `--highlight` |
| `needs_split` | `Scissors` | `--warn` | `--ink` | era `--highlight` |
| `generating` | `Sparkles` | `--signal` | `--ink` | `--status-processing` removido |
| `done` | `CircleCheck` | `--done` | `--ink` | `--status-done` removido |
| `failed` | `CircleAlert` | `--failed` | `--failed` | `--status-failed` removido |

- Estados seguem com ícone e texto, nunca só cor.
- Mensagem de sucesso fora do `StatusBadge` (teste de conexão, salvo, provedor ativo, Parte que cabe) usa `--done`.
- `@theme` em `index.css` troca `--color-highlight*` e `--color-status-*` (linhas 33 a 38) por `--color-canvas`, `--color-surface`, `--color-sunken`, `--color-hairline`, `--color-ink`, `--color-ink-muted`, `--color-signal`, `--color-signal-ink`, `--color-signal-soft`, `--color-done`, `--color-warn`, `--color-warn-soft`, `--color-failed`, `--color-failed-soft` e `--color-scrim`.

#### Classes de cor a trocar (Q1)

- A Task 52 troca, em todo o `src/`, só as classes e referências de cor que dependem de token removido. Motivo: Tailwind v4 não acusa erro quando o token sai; a classe some e o elemento perde a cor sem aviso.
- Demais classes da tela (raio, tamanho arbitrário, `transition-colors`, `ring-ring/50`) ficam para a task da tela (Tasks 53 a 61). Exceção: `app/SamplePage.tsx`, refeita inteira na Task 52.
- Usos conferidos por grep em 2026-10-28:

| Arquivo:linha | Hoje | Destino | Uso |
|---|---|---|---|
| `components/surfaces/StatusBadge.tsx:19` | `text-status-pending` | `text-ink-muted` | `pending` |
| `components/surfaces/StatusBadge.tsx:20` | `text-status-processing` | `text-signal` | `processing` |
| `components/surfaces/StatusBadge.tsx:21` | `text-highlight` | `text-ink` | `transcribed` |
| `components/surfaces/StatusBadge.tsx:22` | `text-highlight` | `text-warn` | `needs_split` |
| `components/surfaces/StatusBadge.tsx:23` | `text-status-processing` | `text-signal` | `generating` |
| `components/surfaces/StatusBadge.tsx:24` | `text-status-done` | `text-done` | `done` |
| `components/surfaces/StatusBadge.tsx:25` | `text-status-failed` | `text-failed` | `failed` |
| `features/backlog-review/MergeNotice.tsx:5` | `text-highlight` | `text-signal` | dica de mesclagem |
| `features/backlog-review/EditableField.tsx:144` | `text-highlight` | `text-signal` | dica do campo (`role="status"`) |
| `features/transcript-split/CutControls.tsx:58` | `border-highlight bg-highlight text-highlight-foreground` | `border-signal bg-signal text-signal-ink` | marcador de corte ativo |
| `features/transcript-split/CutControls.tsx:71` | `bg-highlight` | `bg-signal` | linha de corte |
| `features/llm-providers/ProviderForm.tsx:254`, `:258`, `:260` | `text-status-done` | `text-done` | sucesso (teste de conexão, salvo) |
| `features/llm-providers/SettingsPage.tsx:14` | `text-status-done` | `text-done` | provedor ativo |
| `features/transcript-split/PartSummary.tsx:27` | `text-status-done` | `text-done` | Parte cabe; `text-destructive` segue (apelido) |
| `app/SamplePage.tsx:20` | nome `"highlight"` na lista de tokens | lista dos tokens da tabela "Tokens" | amostra |
| `app/SamplePage.tsx:55` | `rounded-xl bg-gradient-to-br from-highlight to-foreground` | `rounded-lg bg-signal`, sem gradiente | fundo da amostra do vidro |
| `styles/spotlight.css:18` | `var(--highlight)` | `var(--signal)` | realce do upload |
| `components/surfaces/GlassPanel.test.tsx:145` | `t["--highlight"]` | `t["--signal"]` | contraste sobre vidro |
| `styles/tokens.test.ts:47` a `:60`, `:93` | pares e nomes `--highlight*`, `--sidebar-*`, `--status-*` | pares das tabelas de "Contraste" | teste de tokens |

- Grep do checkpoint da Task 52: em `components/`, `styles/`, `index.css` e `app/SamplePage.tsx`, nenhum resultado para `highlight|status-(pending|processing|done|failed)|sidebar|chart-` (forma de variável e forma de classe).
- Usos em `features/` da tabela: conferidos linha a linha no PR da Task 52.

#### Contraste

Conferidos por script em 2026-10-28, contra `--canvas` (claro / escuro):

| Par | Claro | Escuro | Mínimo |
|---|---|---|---|
| `--ink` / `--canvas` | 16,5 | 15,9 | 4,5 |
| `--ink-muted` / `--canvas` | 5,7 | 7,7 | 4,5 |
| `--signal` / `--canvas` | 6,3 | 9,1 | 4,5 |
| `--done` / `--canvas` | 6,2 | 9,6 | 4,5 |
| `--warn` / `--canvas` | 5,4 | 10,0 | 4,5 |
| `--failed` / `--canvas` | 5,8 | 7,2 | 4,5 |
| `--input` / `--canvas` | 3,5 | 4,1 | 3 (UI) |
| `--signal-ink` / `--signal` | 6,3 | 9,1 | 4,5 |
| `--ring` / `--canvas` | 6,3 | 9,1 | 3 (UI) |

Estimados, a conferir em `tokens.test.ts`. Pares contra `--surface` derivados dos valores acima pela luminância do fundo (fundo neutro). Pares do `Notice` estimados por L³ (aproximação de neutro; erro de ±0,3 visto nos pares conferidos):

| Par | Claro | Escuro | Mínimo |
|---|---|---|---|
| `--ink` / `--surface` | ~17,1 | ~14,7 | 4,5 |
| `--ink-muted` / `--surface` | ~5,9 | ~7,1 | 4,5 |
| `--input` / `--surface` | ~3,6 | ~3,8 | 3 (UI) |
| `--ring` / `--surface` | ~6,5 | ~8,4 | 3 (UI) |
| `--done` / `--surface` | ~6,4 | ~8,9 | 4,5 |
| `--warn` / `--surface` | ~5,6 | ~9,2 | 4,5 |
| `--failed` / `--surface` | ~6,0 | ~6,6 | 4,5 |
| `--signal` / `--surface` | ~6,5 | ~8,4 | 4,5 |
| `--primary-foreground` / `--primary` (`--canvas` sobre `--ink`) | 16,5 | 15,9 | 4,5 |
| `--ink` / `--warn-soft`, `--failed-soft`, `--signal-soft` | ~15 | ~13 | 4,5 |
| `--ink-muted` / `--warn-soft`, `--failed-soft`, `--signal-soft` | ~5,2 | ~6,3 | 4,5 |
| `--warn` / `--warn-soft` | ~5,0 | ~8,2 | 4,5 |
| `--failed` / `--failed-soft` | ~5,4 | ~5,9 | 4,5 |
| `--signal` / `--signal-soft` | ~5,7 | ~7,2 | 4,5 |

- Todo texto de estado passa 4,5:1 também sobre `--sunken` e `--signal-soft`.
- `tokens.test.ts` testa todos os pares das duas tabelas, nos dois temas. Par abaixo do mínimo: ajustar o fundo `-soft`, nunca baixar o mínimo.
- `--hairline` é divisor decorativo, sem exigência de 3:1. Borda que identifica controle usa `--input`.

### Foco

- Anel opaco de 2 px em `--ring`, sem alfa. Proibido `ring-ring/50`, `outline-ring/50` e qualquer alfa no anel (no claro, `ring-ring/50` dá cerca de 2,3:1, abaixo de 3:1).
- Base em `index.css`: `outline-ring` sem `/50`. Botão, campo e área de upload usam `focus-visible:ring-2 ring-ring` (ou `outline-2`), com afastamento de 2 px.
- Campo inválido: borda `--failed` opaca. Alfa só em fundo decorativo, nunca em anel nem em borda de controle.

### Tipografia

- Três famílias variáveis, servidas pelo app em `.woff2`, subsets latin e latin-ext por `unicode-range`, licença OFL:
  - Source Serif 4: título de página, Epic, nome de US, fala da Transcrição, título de diálogo, marca;
  - Geist: controles, rótulos, navegação, corpo de UI;
  - Geist Mono, algarismos tabulares: `US-id`, instantes `hh:mm:ss`, tokens, cronômetro, datas e durações em lista.
- `@theme` em `index.css`:
  - `--font-heading` e `--font-serif` apontam para Source Serif 4;
  - `--font-sans` aponta para Geist;
  - `--font-mono` aponta para Geist Mono.
  - Hoje `index.css:12` aponta `--font-heading` para a sans; muda na Task 52.
- Serif nunca em botão, rótulo, campo ou nav.
- Escala (12, 14, 16, 20, 24, 32, 40 px), alturas de linha, pesos (400, 500, 600) e limite de três tamanhos por tela: iguais ao ADR-0022. `text-[0.8rem]` e todo tamanho arbitrário saem.
- Arquivos novos em `frontend/public/fonts/`: quatro `.woff2` (Source Serif 4 latin e latin-ext; Geist Mono latin e latin-ext).
- Licença: `LICENSE-SourceSerif4.txt` (OFL) obrigatório junto dos arquivos. A tarefa confere se `LICENSE-Geist.txt` cobre a Geist Mono; se não cobrir, adiciona o arquivo da licença dela.
- Carga (Q6):
  - `<link rel="preload">` da Geist latin e da Source Serif 4 latin. Geist Mono sem preload.
  - Todas com `font-display: swap`.
  - Fallback local com métricas ajustadas (`size-adjust`, `ascent-override`, `descent-override`, `line-gap-override`) para serif e sans, contra CLS (NFR-05).
  - Contingência: se o LCP do login (NFR-03) passar de 2,5 s, o `h1` do auth troca para Geist. Sem novo ADR.

### Forma

- Espaço: só 4, 8, 12, 16, 24, 32, 48, 64 px em padding, margin e gap. Vale para páginas e para `components/ui/*` (Q7). Em Tailwind: `1`, `2`, `3`, `4`, `6`, `8`, `12`, `16`. Saem `0.5`, `1.5`, `2.5`, `5`, `7` e afins.
- Raio: `--r-4` (badge, tag, skeleton), `--r-6` (botão, campo), `--r-10` (diálogo, popover, painel de gravação, card de auth). Nada acima de 10 px, exceto círculo de ícone (`rounded-full`).
- `@theme` em `index.css` (Q7): `--radius-*: initial`; `--radius-sm` = `--r-4`, `--radius-md` = `--r-6`, `--radius-lg` = `--r-10`. Removidos `--radius-xl` a `--radius-4xl`. `rounded-xl` e acima saem do código.
- Entre a Task 52 e a task de cada tela, `rounded-xl` e acima ficam sem raio (classe sem token). Efeito só visual, aceito na decisão Q1; cada task de tela remove a classe.
- Altura de controle: 36 px padrão, 32 px `sm`. Campo de texto 40 px. Alvo mínimo de 24 px segue. Altura não segue a escala de espaço.
- Larguras: `--shell` 72rem (app), `--reading` 44rem (Transcrição, formulários, nomeação). Página não escolhe `max-w-*` própria.

### Profundidade

- No fluxo: sem sombra, sem fundo de card. Só réguas (`--hairline`; régua forte em `--ink` no topo de lista e de Epic).
- Flutuante: uma elevação só, `--overlay-shadow`. Diálogo e popover sobre `--scrim`.
- `@theme`: `--shadow-*: initial` e só `--shadow-overlay`. Saem `--shadow-sm` e `--shadow-md` (`index.css:31-32`, leem `--elevation-*`). Grep de 2026-10-28: nenhuma classe `shadow-sm` ou `shadow-md` em `src/`.

### Vidro

- Só no painel flutuante da gravação (`RecordingPanel`, Q1). Motivo: o painel é `fixed` no rodapé da página de gravação, sobre o conteúdo rolável; o vidro mantém o conteúdo legível por trás.
- Opacos: barra de navegação, diálogos, confirmações, card de login e cadastro. Toast não existe no código; se vier, nasce opaco.
- `GlassPanel`, receita, fallbacks e a proibição de `backdrop-filter` fora de `glass.css` seguem iguais ao ADR-0022.
- `glass.css` na Task 52:
  - lê `--surface` e `--ink` em vez de `--card` e `--card-foreground` (linhas 5, 6 e 16);
  - `box-shadow: var(--overlay-shadow)` em vez de `var(--elevation-2)` (linha 8), porque `--elevation-2` sai.
- Diálogos que hoje usam `GlassPanel` e passam a `DialogSurface` (opaco):
  - direto: `components/surfaces/ConfirmDialog.tsx`, `features/backlog-review/FormDialog.tsx`, `features/backlog-review/RegenerateDialog.tsx`, `features/screen-recording/SourceWarningDialog.tsx`, `features/llm-providers/RemoveDialog.tsx`;
  - por `ConfirmDialog`: `meetings/DeleteMeetingDialog.tsx`, `meetings/RetryButton.tsx`, `backlog-review/RetryButton.tsx`, `backlog-review/ConfirmDeleteDialog.tsx`;
  - por `FormDialog`: `backlog-review/RenameParticipantDialog.tsx`, `backlog-review/MoveStoryDialog.tsx`;
  - por `RemoveDialog`: `llm-providers/ProviderForm.tsx`.
- Fora de diálogo, saem do `GlassPanel`: `features/auth/AuthShell.tsx` (card opaco, na Task 55) e `app/SamplePage.tsx` (amostra mostra o vidro só como exemplo do painel de gravação).
- Comentários que citam vidro em diálogo mudam na tarefa: `ConfirmDialog.tsx:22`, `FormDialog.tsx:21`, `RemoveDialog.tsx:14`, `AuthShell.tsx:12`, `GlassPanel.tsx:11`, `glass.css:1`, `spotlight.css:1`.

### Mouse-tracking

- Só na área de upload, como realce da borda que segue o ponteiro (Q2, opção A). Login e cadastro sem spotlight.
- `usePointerSpotlight` e regras de ativação seguem iguais ao ADR-0022. O hook grava `--pointer-x` e `--pointer-y`.
- O realce:
  - gradiente radial em `--signal` no `::before` da área;
  - máscara com `mask-composite: exclude` (e `-webkit-mask-composite: xor`) recorta o `::before` para a faixa da borda; o miolo fica transparente;
  - texto e fundo do miolo sem alteração; a borda fixa em `--input` segue identificando o controle;
  - sem suporte a `mask-composite`, o realce não aparece.
- Hoje `spotlight.css` pinta o fundo da área inteira (`::before` com `inset: 0`, sem máscara) e lê `--highlight`. A Task 52 troca só `--highlight` por `--signal`; a Task 57 recorta para a borda e atualiza o comentário da linha 1 (cita login).
- Única exceção ao "sem gradiente". Motivo: efeito decorativo, aprovado na diretriz, desligado em toque, com movimento reduzido e em `forced-colors`; não carrega informação nem muda contraste do texto.

### Movimento

- Tokens e regras do ADR-0022 seguem. Só `transform` e `opacity`.
- Proibido `transition: all` e `transition-colors`. Hover troca cor sem transição. Hoje há um uso de `transition-colors` (`features/meetings/UploadPage.tsx:63`); a Task 57 remove. O grep global do "Checkpoint: Redesign Ata" confere que não há outro.
- Skeleton com respiração lenta de opacidade conta como indicador de progresso (exceção ao "sem laço" do ADR-0022); parado com `prefers-reduced-motion`.
- Usos: os do ADR-0022, mais entrada do card de auth e do diálogo por opacidade. Sem troca de rota animada.

### Tema

- Controle visível de tema (claro, escuro, sistema) no `AppShell` e na tela de auth (Q4). Componente `ThemeToggle` em `components/surfaces/`.
- Remover o atalho de tecla `d` do `theme-provider.tsx` (WCAG 2.2, 2.1.4: atalho de uma tecla sem modo de desligar).
- Preferência em `localStorage` (preferência visual, já permitida no ADR-0022 e no `02-architecture.md`). Sessão nunca.
- `frontend/index.html:6-7`: `<meta name="theme-color">` acompanha `--canvas` claro e escuro (hoje `#ffffff` e `#0a0a0a`). Valor em hex equivalente ao `oklch` do token, conferido na Task 52.

### Componentes

Pasta: `components/surfaces/` para todos os primitivos novos. `app/Layout.tsx` segue em `app/` e passa a compor o `AppShell`: guarda sessão, logout e links; `AppShell` só desenha. Motivo: `components/` não importa `features/` (`useSession`).

- Regra aplicada por ESLint na Task 52: `no-restricted-imports` em `components/**` barra `@/features/*` (`frontend/eslint.config.js`; hoje sem regra).
- `AppShell`: marca em serif, nav com sublinhado de 2 px em `--signal` no item ativo (`aria-current="page"`), largura `--shell`, `ThemeToggle`, barra opaca.
- `PageHeader`: título serif, descrição em `--ink-muted`, ações à direita.
- `Notice` (Q5):
  - substitui só alertas de bloco e de página (as 13 caixas da auditoria);
  - erro de campo fica inline no `FormField`, sem `Notice`;
  - variantes: `info` (fundo `--signal-soft`, régua `--signal`), `warn` (fundo `--warn-soft`, régua `--warn`), `error` (fundo `--failed-soft`, régua `--failed`), `consent` (fundo `--sunken`, régua `--ink-muted`);
  - régua esquerda de 2 px, texto em `--ink`, ícone na cor da variante;
  - `error` com `role="alert"`; `info` e `warn` com `role="status"`; `consent` sem região viva.
- `ConsentNotice` segue componente próprio em `components/surfaces/ConsentNotice/`. Na Task 52 passa a renderizar `Notice variant="consent"` com `CONSENT_NOTICE_TEXT` intacto (`meetings` critério 52, `screen-recording` critério 26). Teste de igualdade com `CONSENT_NOTICE_TEXT` na mesma task. Tasks 57 e 61 só posicionam o componente na tela.
- `Skeleton` e `EmptyState` únicos.
- `DialogSurface`: superfície opaca de diálogo (`--surface`, `--r-10`, `--overlay-shadow`, sobre `--scrim`). Usada por todo diálogo.
- `StatusBadge`: sem pílula com borda; cores da tabela "Estados".
- `Button` (tabela abaixo): `accent` só no passo que avança o fluxo, no máximo um por tela.
- Backlog: US como linha com régua, não card.

| Variante antiga | Variante nova | Visual |
|---|---|---|
| `default` | `primary` | fundo `--ink`, texto `--canvas` |
| (nova) | `accent` | fundo `--signal`, texto `--signal-ink` |
| `outline` | `secondary` | fundo transparente, borda `--input`, texto `--ink`, hover `--sunken` |
| `secondary` | `secondary` | idem (um uso hoje, `ProviderForm.tsx:291`) |
| `ghost` | `ghost` | sem borda, hover `--sunken` |
| `destructive` | `danger` | texto `--failed`, borda `--failed`, hover `--failed-soft` |
| `link` | removida | sem uso hoje; link de texto usa `<Link>` com `--ink` sublinhado |

- Tamanhos ficam: `default` 36 px, `sm` 32 px, `icon` 36 px, `icon-sm` 32 px.
- Tamanhos que saem, com destino dos usos (grep de 2026-10-28):
  - `xs` e `icon-xs`: saem; sem uso fora de `components/ui/button.tsx`;
  - `lg`: sai; `LoginPage.tsx:72` e `RegisterPage.tsx:85` passam a `default` (36 px);
  - `icon-lg`: sai; `SpeakerRow.tsx:41` passa a `icon`.
- Renomes de variante e saída de tamanho trocam os usos em todo o `src/` na própria Task 52, porque o tipo de `variant` e `size` deixa de aceitar o nome antigo e `npm run typecheck` falha. Grep de 2026-10-28: 22 usos de `variant` em 17 arquivos (literais, `buttonVariants({ variant })` em `ExportButtons.tsx:15,23` e ternários em `ConfirmDialog.tsx:56` e `SpeakerRow.tsx:40`), mais os três de `size` acima. Regra: todo uso que o `typecheck` acusar. Task 52 também troca `defaultVariants` e o padrão `variant = "default"` em `button.tsx`. Usos sem `variant` explícito pegam `primary` pelo padrão.

## Consequências

- Sem dependência npm nova. Quatro arquivos de fonte novos e a licença da Source Serif 4 em `frontend/public/fonts/`. Peso medido no PR da tarefa; NFR-03 (LCP do login) e NFR-05 (CLS) remedidos.
- NFR-06 (máximo 3 vidros) segue; na prática fica 1. NFR-08 vale só para a área de upload.
- Critérios já entregues que mudam e precisam de revisão na fase de redesign (`tasks/plan.md`, Fase 9):
  - diálogos com `GlassPanel` (Tasks 17, 22, 28, 49): passam a `DialogSurface`;
  - card de vidro e spotlight no login e cadastro (Tasks 9 e 10): opaco, sem spotlight;
  - barra de navegação (`02-architecture.md`, "Mapa de superfícies"): opaca.
- Testes a atualizar:
  - `RegenerateDialog.test.tsx`, `MeetingDetailPage.test.tsx`, `meetings/RetryButton.test.tsx`, `ProviderForm.test.tsx`: afirmam `data-slot="glass-panel"` em diálogo; passam a afirmar `DialogSurface`;
  - `GlassPanel.test.tsx`: usa `--card`, `--card-foreground`, `--highlight`; passa a `--surface`, `--ink`, `--signal`;
  - `SamplePage.test.tsx`: amostra com tokens e componentes novos;
  - `tokens.test.ts`: pares e nomes antigos (`--highlight*`, `--status-*`, `--sidebar-*`); passa aos pares das tabelas de contraste deste ADR;
  - `ConsentNotice.test.tsx`: afirma `Notice variant="consent"` e texto igual a `CONSENT_NOTICE_TEXT` (Task 52).
- `no-stray-backdrop.test.ts` segue válido sem mudança de regra.
- Testes novos:
  - na Task 52: nenhum diálogo renderiza `GlassPanel`; `ThemeToggle` acessível por teclado; nenhum listener de `keydown` no `theme-provider`; grep restrito de "Classes de cor a trocar";
  - a partir do "Checkpoint: Redesign Ata" (`tasks/plan.md`): teste estático global sem `rounded-xl` ou acima, `transition-colors`, `ring-ring/50`, `outline-ring/50` ou `text-[` em `src/`. Antes disso as telas ainda não migradas teriam falha esperada.
- Implementação por fatias: tokens, primitivos, classes de cor e usos de `Button` de todo o `src/`, depois shell + lista de reuniões, depois revisão do backlog, depois o resto, uma tela por vez. Lógica, rotas e integrações não mudam.
