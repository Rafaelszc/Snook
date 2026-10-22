# ADR-0008: Sessão por cookie opaco guardado no servidor

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q3 da rodada de decisões do planner: cookie opaco no servidor, com inatividade de 24 h e máximo de 7 dias. Recomendação aceita sem mudança.

## Contexto

- `auth` pede mecanismo e duração da sessão.
- Logout precisa invalidar a sessão no servidor (`auth`, critério 17).
- Nunca guardar token de sessão em storage acessível ao JavaScript.
- Frontend e API na mesma origem (ADR-0016).

## Opções consideradas

1. **Cookie com token aleatório opaco; sessão numa tabela `sessions` (hash SHA-256 do token).**
   - Prós: logout e expiração reais; nada sensível no cliente; simples.
   - Contras: uma leitura no banco por requisição (barata no SQLite).
2. **JWT em cookie `httpOnly`.**
   - Prós: sem leitura de sessão.
   - Contras: logout não invalida sem lista de revogação; segredo de assinatura a mais; payload legível.
3. **JWT em `localStorage` com header `Authorization`.**
   - Prós: imune a CSRF.
   - Contras: exposto a XSS; viola a regra "Never" do 03-security.

## Decisão

Opção 1.

- Cookie `snook_session`: `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` quando servido em HTTPS (`SESSION_COOKIE_SECURE`, padrão `auto`: liga em HTTPS e em `localhost`).
- Token: 32 bytes de `secrets.token_urlsafe`. Banco guarda só o SHA-256.
- Expiração: inatividade de 24 h e máximo absoluto de 7 dias. Valores em configuração.
- Novo token a cada login e no cadastro (sem fixação de sessão).
- Logout apaga a linha da sessão e o cookie.
- Sessões vencidas apagadas no startup e a cada hora.
- CSRF: `SameSite=Lax` mais checagem de `Origin` (ou `Referer`) em todo método que muda estado, contra a lista `ALLOWED_ORIGINS`. Pedido sem `Origin` válido recebe HTTP 403.
- Dependência FastAPI `current_user` em `modules/auth/deps.py`. Sem sessão válida: HTTP 401 antes de qualquer lógica.

## Consequências

- Nenhum segredo de assinatura extra no `.env`.
- Testes usam o cookie do `TestClient`.
