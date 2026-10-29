# ADR-0016: Frontend e API na mesma origem; bind local por padrão; HTTPS para uso na rede

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q11 da rodada de decisões do planner: bind local por padrão e HTTPS no perfil `lan`. Recomendação aceita sem mudança.

## Contexto

- Q60: app roda na máquina do usuário ou em rede confiável.
- `getDisplayMedia` e `getUserMedia` só funcionam em contexto seguro: `https://` ou `http://localhost`. Em `http://192.168.x.x`, a gravação de tela não funciona.
- Cookie com `Secure` não é gravado em HTTP fora de `localhost`.
- Origem única dispensa CORS.
- App em `localhost` é alvo de DNS rebinding a partir de site malicioso aberto no navegador.

## Opções consideradas

1. **nginx no container `frontend` serve o build e faz proxy de `/api` para o backend. Porta publicada em `127.0.0.1` por padrão. Uso na rede por perfil `lan` com Caddy e `tls internal`.**
   - Prós: mesma origem; sem CORS; localhost funciona sem certificado; rede ganha HTTPS.
   - Contras: no perfil `lan`, cada máquina cliente precisa confiar na CA local do Caddy.
2. **Mesma origem, HTTP sempre, porta em `0.0.0.0`.**
   - Prós: simples.
   - Contras: gravação de tela quebra na rede; cookie sem `Secure`; sessão em texto claro na rede.
3. **Frontend e API em portas separadas, com CORS.**
   - Contras: CORS a configurar; cookie entre origens; mais superfície.

## Decisão

Opção 1.

- `frontend` publica `${SNOOK_BIND:-127.0.0.1}:${SNOOK_PORT:-8080}:80`.
- `backend` não publica porta. Só a rede interna do compose o alcança.
- Perfil `lan`: serviço `caddy` publica 443 com `tls internal`, envia HSTS e repassa ao `frontend`. README explica como confiar na CA.
- `SNOOK_LAN_HOST` (nome ou IP do servidor) entra em `ALLOWED_HOSTS` e, como `https://<host>`, em `ALLOWED_ORIGINS`.
- Backend aceita `X-Forwarded-For` e `X-Forwarded-Proto` só de `TRUSTED_PROXY_IPS` (IPs fixos de nginx e Caddy). nginx repassa `X-Forwarded-Proto` só quando a conexão vem do Caddy.
- Backend aceita só `Host` da lista `ALLOWED_HOSTS` (padrão `localhost,127.0.0.1`) via `TrustedHostMiddleware`. Barra DNS rebinding.
- CORS desligado. Nenhum header `Access-Control-Allow-Origin` é enviado.
- Detalhe (Caddyfile, `map` do nginx, passos da CA): `08-deployment.md`, "Perfil lan". Detalhes adicionados em 2026-10-22, na rodada de correções da revisão do spec-reviewer, sem mudar a decisão.

## Consequências

- Uso na rede sem o perfil `lan` funciona para upload, mas não para gravação de tela. README avisa; a tela de gravação mostra a mensagem de `screen-recording` critério 27.
- `SESSION_COOKIE_SECURE=auto` liga `Secure` no perfil `lan`, porque o esquema `https` chega ao backend pelo proxy confiável.
- Limite de login por IP (ADR-0010) conta o IP do cliente da rede, não o do proxy.
- Volume `caddy-data` guarda a chave da CA local e é tratado como segredo.
- Nota no spec (Q60) sobre HTTPS na rede: mudança aprovada pelo usuário em 2026-10-22. Aplicado em `00-overview.md` e `01-prd.md` (critério transversal 22, US 26) e em `01-prd/screen-recording.md` (critérios 27 e 28).
