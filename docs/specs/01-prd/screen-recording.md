# 01-prd/screen-recording - PRD do módulo `screen-recording`

> Status: completo. Decisões fechadas: Q1, Q26, Q36 (substitui a Q24), Q42, Q53, Q56, Q61, Q70 (ADR-0016, ADR-0018, LGPD), Q71, Q72.
> Visão e capability map: `docs/specs/00-overview.md`. Requisitos transversais: `docs/specs/01-prd.md`. Rotas sem o prefixo `/api` (ver `01-prd.md`, "Convenção de rotas").
> Depende de: `meetings` (criação de Reunião). Dependentes: nenhum.

## Problem Statement

- Muita reunião acontece em chamada no navegador ou em app de videoconferência. Usuário nem sempre tem gravação pronta.
- Gravar com outra ferramenta, salvar e depois enviar é trabalho extra.
- Quem grava com fone de ouvido costuma perder a própria voz. Pedidos dele somem do backlog.

## Solution

- Botão "Gravar reunião" na mesma área do upload.
- Antes de gravar, app lembra o Usuário de obter o consentimento dos participantes (LGPD).
- App pede compartilhamento de tela (ou aba) com áudio e acesso ao microfone. Grava os dois misturados numa trilha só.
- Vídeo não é gravado.
- Falta uma fonte: app avisa; usuário grava só com a que existe ou cancela. Nenhuma fonte: gravação recusada.
- Gravação para sozinha em 1h59m50s, abaixo do limite de 2 h.
- Ao parar: usuário confere título, pré-preenchido com o nome gerado do arquivo. App envia o áudio como nova Reunião, mesmo caminho do upload.
- Gravação só funciona em contexto seguro (`http://localhost` ou HTTPS). Na rede, o app precisa do perfil `lan`.

## User Stories

1. Como usuário, quero escolher entre enviar um arquivo e gravar a reunião, para usar a opção que tenho no momento.
2. Como usuário, quero gravar o som da tela ou da aba da reunião e a minha voz ao mesmo tempo, para que todos os pedidos, inclusive os meus, entrem no backlog.
3. Como usuário, quero ser avisado quando o som da tela ou o microfone não estiver disponível e escolher se gravo só com o que há, para não perder a reunião.
4. Como usuário, quero que o app recuse a gravação quando não houver nenhuma fonte de áudio, para não gerar um arquivo vazio.
5. Como usuário, quero ver há quanto tempo estou gravando e parar quando quiser, para controlar a gravação.
6. Como usuário, quero que o vídeo da tela não seja guardado, para economizar espaço e não guardar imagens que não interessam.
7. Como usuário, quero dar um título à gravação ao parar, já preenchido com o nome do arquivo, para reconhecê-la depois na lista.
8. Como usuário, quero que a gravação vire uma Reunião ao confirmar o envio, para não precisar salvar e enviar um arquivo.
9. Como usuário, quero informar, de forma opcional, quantas pessoas participaram, como no upload, para melhorar a separação das vozes.
10. Como usuário, quero tentar enviar de novo quando a rede falhar, sem gravar de novo, para não perder a reunião.
11. Como usuário, quero saber quando meu navegador não tem suporte oficial à gravação, para usar Chrome ou Edge, ou enviar um arquivo.
12. Como usuário, quero que a gravação pare sozinha pouco antes do limite de 2 h, para que o servidor não recuse o arquivo.
13. Como usuário, quero ser lembrado de obter o consentimento dos participantes antes de gravar, para cumprir a LGPD.
14. Como usuário que abre o app pela rede sem HTTPS, quero saber por que a gravação não está disponível e o que fazer, para não achar que o app está quebrado.

## Escopo

- Botão "Gravar reunião" ao lado do upload.
- Aviso de consentimento dos participantes (LGPD) antes de iniciar a gravação (Q70, Q72).
- Checagem de contexto seguro antes de oferecer a gravação (Q70, ADR-0016).
- Captura do som da tela ou aba (`getDisplayMedia` com áudio) e do microfone (`getUserMedia`).
- Checagem das fontes antes de começar: aviso e escolha quando falta uma; recusa quando faltam as duas.
- Mistura das fontes numa trilha só, no navegador.
- Gravação só de áudio, em webm; vídeo descartado.
- Tela de gravação com tempo decorrido e botão "Parar".
- Parada automática em 1h59m50s (Q61).
- Tela de envio com título pré-preenchido e número opcional de participantes.
- Envio pela criação de Reunião de `meetings`, com reenvio em falha de rede.
- Aviso de suporte oficial só em Chrome e Edge.

## Fora de escopo

- Trilhas separadas para tela e microfone (Q42).
- Gravação de vídeo (Q36).
- Pausar e retomar a gravação.
- Transcrição durante a gravação (não-objetivo "tempo real").
- Gravar sem o app aberto, ou fora do navegador.
- Validação de formato, tamanho e duração no servidor. É de `meetings`.
- Configurar HTTPS. Fica com o Operador, pelo perfil `lan` (`08-deployment.md`, ADR-0016).
- Guardar prova do consentimento dos participantes (`03-security.md`, "Privacidade (LGPD)").

## Restrições

| Restrição | Fonte |
|---|---|
| Primeira versão com só duas entradas: gravação de tela ou envio de áudio. | rodada 1, Q1 |
| Capta o som da aba ou do sistema, conforme o navegador oferecer, e também a voz do usuário (microfone). | rodada 3, Q36 (substitui a Q24) |
| Vídeo descartado; só áudio guardado, em webm. | rodada 3, Q36 |
| Limite de 2 h; a gravação para sozinha em 1h59m50s. | rodada 3, Q36; Q61 |
| Suporte oficial em Chrome e Edge. | rodada 3, Q36 |
| Uma trilha só, misturada no navegador. | rodada 4, Q42 |
| Falta uma das fontes: aviso e escolha entre gravar só com a disponível ou cancelar. | rodada 4, Q42 |
| Sem nenhuma fonte de áudio: gravação recusada com mensagem. | rodada 4, Q42 |
| Campo opcional de número de participantes, de 1 a 20. | rodada 2, Q26; Q56; Q70 (`05-api.md`) |
| Campo `title` opcional também na gravação, pré-preenchido com o nome do arquivo. | Q53 |
| Comportamentos de parada, saída da página, reenvio e aviso de navegador (critérios 10 a 12, 16, 19 e 23). | Q56 |
| A Reunião é criada pela mesma regra do upload (formatos, 2 h, 500 MiB); o servidor lê a duração do webm do `MediaRecorder`. | `meetings.md`, contrato "Criar Reunião"; Q61; Q70 (ADR-0018) |
| `getDisplayMedia` e `getUserMedia` exigem contexto seguro (`https://` ou `http://localhost`). Na rede, o app usa HTTPS pelo perfil `lan`. | Q70 (ADR-0016) |
| Aviso de consentimento dos participantes (LGPD) antes de iniciar a gravação, com o texto literal da Q72. | Q70 (`03-security.md`, LGPD); Q72 |
| Codec `audio/webm;codecs=opus` a 64 kbps; mistura pela Web Audio API; pedido da tela antes do microfone. | ADR-0015 |
| React + TypeScript + shadcn/ui no frontend. | briefing |

## Contrato com outros módulos

- Módulo não tem backend próprio. Envia o arquivo pelo endpoint de criação de Reunião de `meetings` (`POST /meetings`, sugerido): `file` em webm só de áudio, `title` e `expected_speakers` opcional.
- Reunião da gravação é igual a Reunião de upload: mesmo status inicial (`pending`), mesmo aviso "Reunião criada", mesmo pipeline, mesmo "Tentar novamente".
- Recusas do servidor (formato, tamanho, duração, arquivo sem áudio, título) seguem regras e mensagens de `meetings`.
- Aviso de consentimento usa o mesmo componente e a mesma constante de texto da tela de upload (`meetings`, critério 52).

## Critérios de aceite

### Início e fontes

1. A área autenticada oferece duas opções de entrada: enviar arquivo e "Gravar reunião".
2. Ao clicar em "Gravar reunião", o app pede o compartilhamento de tela ou aba com áudio e o acesso ao microfone.
3. Com som da tela e microfone disponíveis, a gravação começa sem aviso extra. O arquivo final contém os dois sons misturados numa única trilha de áudio.
4. Com microfone disponível e sem trilha de áudio da tela, o app mostra um aviso que nomeia a fonte ausente, com as opções "Gravar só com o microfone" e "Cancelar". Nada é gravado antes da escolha.
5. Com som da tela disponível e microfone negado ou ausente, o app mostra um aviso que nomeia a fonte ausente, com as opções "Gravar só com o som da tela" e "Cancelar". Nada é gravado antes da escolha.
6. Sem nenhuma fonte de áudio, o app recusa a gravação com uma mensagem, não grava nada e não cria Reunião.
7. Ao cancelar no aviso, o app encerra o compartilhamento de tela e o acesso ao microfone, não grava nada e não cria Reunião.

### Durante a gravação

8. A tela de gravação mostra o tempo decorrido e um botão "Parar".
9. O arquivo enviado tem só trilha de áudio, sem trilha de vídeo.
10. Ao atingir 1h59m50s, a gravação para sozinha e segue para a tela de envio, com um aviso de que o limite foi atingido. O arquivo resultante tem no máximo 1h59m50s de áudio.
11. Se o usuário encerra o compartilhamento pela barra do navegador, a gravação para como se ele tivesse clicado em "Parar".
12. Sair da página ou fechá-la durante a gravação, ou antes do envio, pede confirmação do navegador.

### Fim e envio

13. Ao parar, o app encerra o compartilhamento de tela e o acesso ao microfone.
14. Ao parar, o app gera o nome do arquivo no padrão `gravacao-AAAA-MM-DD-HHhMM.webm`, com a data e a hora local do início da gravação.
15. A tela de envio mostra o campo de título preenchido com o nome do arquivo gerado, e o usuário pode alterá-lo antes de enviar.
16. A tela de envio oferece também o campo opcional de número de participantes, com a mesma validação do upload.
17. O envio cria uma Reunião pelo endpoint de `meetings`, com o título da tela de envio. A Reunião aparece na lista com esse título e status `pending`, e segue o mesmo fluxo de uma Reunião enviada por arquivo.
18. Uma recusa do servidor aparece na tela com a mensagem devolvida pela API.
19. Numa falha de rede no envio, o app mostra o erro e um botão "Tentar de novo", que reenvia a mesma gravação sem gravar de novo, enquanto a página estiver aberta.
20. Após o envio bem-sucedido, o app leva o usuário ao detalhe da nova Reunião.

### Navegadores

21. Em Chrome e Edge atuais, compartilhar uma aba com áudio produz uma gravação com o som da aba e o microfone.
22. Em navegador sem `getDisplayMedia` ou sem `MediaRecorder` com suporte a webm, o botão "Gravar reunião" fica desabilitado, com mensagem que indica Chrome ou Edge e lembra que o envio de arquivo continua disponível.
23. Em navegador que tem as duas APIs, mas não é Chrome nem Edge, o app avisa que o suporte oficial é só desses dois, sem bloquear a gravação.

### Tamanho e servidor

24. A taxa de bits da gravação mantém uma gravação de 1h59m50s abaixo de 524.288.000 bytes (500 MiB, ADR-0018).
25. `POST /meetings` aceita um arquivo webm só de áudio no formato produzido pela gravação, sem duração no cabeçalho (fixture gerada a partir do próprio gravador), e grava a duração real (`meetings`, critério 47).

### Aviso de consentimento (Q70, Q71, Q72, LGPD)

26. A área de gravação mostra o aviso de consentimento dos participantes junto do botão "Gravar reunião", visível antes de a gravação começar. O aviso exibe o texto literal fixado em `meetings`, critério 52 (Q72), vindo da mesma constante única do frontend. O teste desta tela compara o texto exibido com essa constante. O aviso é só texto: não pede confirmação nem bloqueia a gravação (Q71).

### Contexto seguro (Q70, ADR-0016)

27. Com o app aberto fora de contexto seguro (`window.isSecureContext` falso, por exemplo em `http://192.168.0.10:8080`), o botão "Gravar reunião" fica desabilitado. A mensagem diz que a gravação exige HTTPS ou `localhost`, que o Operador pode ativar o perfil `lan`, e que o envio de arquivo continua disponível. Essa mensagem tem prioridade sobre a do critério 22.
28. Em `http://localhost` e em `https://` (perfil `lan`, com a CA local confiada no cliente), a checagem do critério 27 não bloqueia a gravação.

## Estratégia de testes (seam da Q32 no backend; seam de frontend abaixo)

- **Seam principal (frontend):** lógica da gravação atrás de interfaces para `getDisplayMedia`, `getUserMedia`, `MediaRecorder` e `isSecureContext` (`DisplayCapture`, `MicCapture`, `Recorder`, `Clock`, ADR-0015). Fakes simulam cada combinação de fontes (as duas, só tela, só microfone, nenhuma), fim do compartilhamento pelo navegador, parada em 1h59m50s com relógio falso e contexto inseguro. Cobre critérios 1 a 8, 10 a 20, 22, 23, 26, 27 e 28 (este com fake). Framework: Vitest + React Testing Library + MSW. Resolvido: ADR-0015.
- **Backend (critério 25):** API HTTP via `TestClient` no Pytest (seam da Q32), com fixture webm só de áudio, sem duração no cabeçalho.
- **Arquivo real (critérios 3, 9, 21 e 24):** teste manual em checklist, em Chrome e Edge, no Windows e no Linux (Fedora). Cada execução confere com `ffprobe`: uma só trilha de áudio, nenhuma de vídeo, tamanho dentro da projeção para 1h59m50s.
- **Perfil `lan` real (critério 28):** checagem manual junto do critério transversal 22 de `01-prd.md`.

## Questões em aberto

1. Q71 fechada em 2026-10-22: aviso é só texto visível, sem confirmação obrigatória. Q72 fechada em 2026-10-22: texto literal do aviso (`meetings`, critério 52).
2. "Tentar novamente" após `failed` (Q54) vale para Reunião da gravação sem nada específico deste módulo. O "Tentar de novo" do critério 19 é outra coisa: reenvio do arquivo quando o upload falha, antes de a Reunião existir.
3. Riscos a verificar na implementação:
   - **Áudio do sistema no Linux.** Até onde se sabe, Chrome e Edge captam áudio do sistema inteiro só no Windows e no ChromeOS. No Linux e no macOS, em geral só áudio de aba. Usuário usa Fedora. Critério 21 exige só áudio de aba; áudio do sistema inteiro no Linux fica a verificar.
   - **Eco.** Sem fone, microfone capta também os alto-falantes. Duplica vozes na trilha misturada e pode atrapalhar a diarização. UI pode recomendar fone; não decidido.
   - **Perda da gravação.** Gravação fica na memória do navegador até o envio. Fechar a aba antes do envio perde a reunião, apesar da confirmação do critério 12. Baixar cópia local: não decidido.
4. Respondidas pelo planner: codec `audio/webm;codecs=opus` a 64 kbps (cerca de 58 MB em 1h59m50s); mistura pela Web Audio API; tela pedida antes do microfone; framework de teste do frontend. Resolvido: ADR-0015.
