# ADR-0004: App somente local e regras da URL do Ollama

- Status: Aceita
- Data: 2026-10-22
- Fonte: Q60, Q63; RT-15.

## Contexto

App roda na máquina do usuário ou em rede confiável. Não fica exposto à internet. Usuário pode ter Ollama em qualquer host da rede.

## Decisão

- Sem exposição à internet.
- URL do Ollama aceita qualquer host, inclusive `localhost`, `host.docker.internal` e rede privada.
- Só esquemas `http` e `https`. Nenhum redirecionamento é seguido.
- URL com credenciais embutidas (`http://usuario:senha@host`) é recusada.
- Limite de tentativas no login e no "Testar conexão". Limite de Reuniões processando por Usuário. Valores: ADR-0010.

## Consequências

- Risco aceito: Usuário autenticado pode apontar a URL do Ollama para serviço interno da rede (SSRF por desenho). Mitigação parcial: sem redirecionamento, timeout, teto de tamanho da resposta, resposta crua nunca devolvida à UI (só motivo tipado). Ver `03-security.md`.
- Se a implantação mudar para internet, este ADR e o 03-security precisam de revisão antes.
