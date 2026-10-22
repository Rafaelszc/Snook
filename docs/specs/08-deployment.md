# 08 - Implantação: Snook

> Status: planner, 2026-10-22. Correções da revisão do spec-reviewer aplicadas em 2026-10-22 (seção "Perfil lan", CLI de escrita, variante GPU). Segunda revisão aplicada em 2026-10-22: testes e verificação manual do perfil `lan` repartidos entre os checkpoints Fundação, `auth` e `screen-recording` de `tasks/plan.md`; conferência do `docker compose stop` na Task 6.
> Justificativa do arquivo: RT-12 e critérios transversais 1, 2, 8, 14, 21 e 22; perfis CPU e GPU (Q5); segredos no `.env` (Q17, Q33); volumes (Q40, Q41); HTTPS na rede (Q70, ADR-0016).

## Ambientes

| Ambiente | Onde | Como sobe |
|---|---|---|
| Desenvolvimento | máquina do desenvolvedor | `uv run uvicorn snook.main:app --reload` e `npm run dev` (proxy do Vite para `/api`), ou `docker compose up --build` |
| Teste | CI e máquina local | `uv run pytest`; `npm test -- --run` |
| Uso local | máquina do Usuário | `docker compose up -d` |
| Uso em rede confiável | servidor na rede | `COMPOSE_PROFILES=cpu,lan docker compose up -d` (ou `gpu,lan`). Ver "Perfil lan" |

Sem ambiente na internet (Q60).

## Serviços do `compose.yaml`

| Serviço | Imagem | Perfil | Portas | Volumes |
|---|---|---|---|---|
| `backend` | `backend/Dockerfile` (Python 3.12 slim, ffmpeg, torch CPU) | `cpu` | nenhuma publicada; 8000 na rede interna | `snook-db:/data`, `./audios:/audios`, `snook-models:/models` |
| `backend-gpu` | `backend/Dockerfile.gpu` (base CUDA, torch CUDA) | `gpu` | idem; alias de rede `backend` | idem; `deploy.resources.reservations.devices` NVIDIA |
| `frontend` | `frontend/Dockerfile` (build Node, runtime nginx) | sempre | `${SNOOK_BIND:-127.0.0.1}:${SNOOK_PORT:-8080}:80` | nenhum |
| `caddy` | `caddy` (digest fixo) | `lan` | `443:443` | `caddy-data:/data`, `deploy/Caddyfile` só leitura |

- Perfil padrão: `.env.example` traz `COMPOSE_PROFILES=cpu`. Assim, `docker compose up` sobe CPU sem flag (critério transversal 1). GPU: trocar para `COMPOSE_PROFILES=gpu`.
- `backend` e `backend-gpu` nunca sobem juntos. Ambos usam alias de rede `backend`, e o nginx aponta para `backend:8000`.
- Rede `snook-net` com sub-rede fixa `172.28.0.0/24`. IPs fixos: `frontend` `172.28.0.10`, `caddy` `172.28.0.11`. Os IPs alimentam `TRUSTED_PROXY_IPS` e o `map` do nginx.
- `snook-db` e `snook-models`: volumes nomeados. Sobrevivem a `docker compose down`; somem só com `down -v` (Q40).
- `snook-db` guarda também a trava `/data/snook.lock` (ADR-0006).
- `./audios`: bind mount, fora do git (Q41).
- Usuário dos containers: UID 1000. `./audios` precisa ser gravável por esse UID; README traz `mkdir -p audios`.
- Healthcheck do backend: `GET /api/health`. `frontend` usa `depends_on: condition: service_healthy`. O perfil GPU usa o mesmo healthcheck.
- Logs: driver `json-file`, `max-size: 10m`, `max-file: 5`.
- Imagens base fixadas por digest (SEC-21).

## Variáveis de ambiente (`.env`)

| Variável | Obrigatória | Padrão | Uso |
|---|---|---|---|
| `COMPOSE_PROFILES` | sim | `cpu` | `cpu` ou `gpu`, mais `lan` opcional |
| `SNOOK_MASTER_KEY` | sim | (vazio no exemplo) | cifra das chaves de LLM (ADR-0009) |
| `SNOOK_MASTER_KEY_PREVIOUS` | não | | rotação |
| `HF_TOKEN` | sim na primeira execução | (vazio) | download do Pyannote |
| `SNOOK_BIND` | não | `127.0.0.1` | interface publicada do `frontend` |
| `SNOOK_PORT` | não | `8080` | porta publicada do `frontend` |
| `SNOOK_LAN_HOST` | sim com perfil `lan` | (vazio) | nome ou IP do servidor na rede; ver "Perfil lan" |
| `ALLOWED_HOSTS` | não | `localhost,127.0.0.1` (mais `SNOOK_LAN_HOST`, se definido) | SEC-14 |
| `ALLOWED_ORIGINS` | não | `http://localhost:8080,http://127.0.0.1:8080` (mais `https://<SNOOK_LAN_HOST>`, se definido) | SEC-04 |
| `SESSION_COOKIE_SECURE` | não | `auto` | ADR-0008 |
| `SESSION_IDLE_SECONDS` / `SESSION_MAX_SECONDS` | não | `86400` / `604800` | ADR-0008 |
| `BCRYPT_ROUNDS` | não | `12` | ADR-0021 |
| `LOGIN_MAX_FAILURES`, `LOGIN_MAX_FAILURES_PER_IP`, `LOGIN_WINDOW_SECONDS` | não | `5`, `20`, `900` | ADR-0010 |
| `LLM_TEST_MAX_CALLS`, `LLM_TEST_WINDOW_SECONDS` | não | `10`, `600` | ADR-0010 |
| `TRANSCRIPTION_MAX_PER_USER`, `TRANSCRIPTION_WORKERS`, `GENERATION_WORKERS` | não | `1`, `2`, `2` | ADR-0010 |
| `TRUSTED_PROXY_IPS` | não | `172.28.0.10,172.28.0.11` | IPs de nginx e Caddy; ADR-0010, "Perfil lan" |
| `UPLOAD_MAX_BYTES` | não | `524288000` | ADR-0018 |
| `MAX_AUDIO_SECONDS` | não | `7200` | Q6 |
| `LLM_READ_TIMEOUT` | não | `300` | ADR-0012 |
| `WHISPER_MODEL`, `WHISPER_COMPUTE_TYPE`, `WHISPER_REVISION` | não | `large-v3-turbo`, `int8`, hash fixo | ADR-0014 |
| `PYANNOTE_PIPELINE`, `PYANNOTE_REVISION` | não | `pyannote/speaker-diarization-3.1`, hash fixo | ADR-0014 |
| `MODELS_OFFLINE` | não | `false` | critério transversal 14 |
| `LOG_LEVEL` | não | `INFO` | 07 |
| `DATABASE_PATH`, `AUDIO_ROOT`, `MODELS_ROOT` | não | `/data/snook.db`, `/audios`, `/models` | caminhos |

- `.env.example` versionado, sem valores secretos (critério transversal 8). Traz o comando que gera `SNOOK_MASTER_KEY`.
- `.gitignore`: `.env`, `*.db`, `*.db-*`, `*.db.bak-*`, `audios/`, `models/`, `node_modules/`, `.venv/`, `dist/`, `__pycache__/`, `.pytest_cache/`, `snook-lan-ca.crt`.
- `ALLOWED_HOSTS` e `ALLOWED_ORIGINS` explícitos no `.env` substituem o padrão inteiro. Nesse caso, o Operador inclui o host da rede à mão.

## Primeira execução

1. `cp .env.example .env` e preencher `SNOOK_MASTER_KEY` e `HF_TOKEN`.
2. Aceitar os termos dos modelos Pyannote no HuggingFace com a conta do `HF_TOKEN`.
3. `mkdir -p audios`.
4. `docker compose up -d --build`.
5. `docker compose exec backend python -m snook.cli download-models` (opcional; senão baixa na primeira transcrição). No perfil GPU, troque `backend` por `backend-gpu`.
6. Abrir `http://localhost:8080`.
7. Opcional, para rodar offline: `MODELS_OFFLINE=true` no `.env` e `docker compose up -d`.

## Perfil lan

Atende o critério transversal 22 e a US 26 do `01-prd.md`, e o critério 28 de `screen-recording` ([ADR-0016](adrs/0016-implantacao-mesma-origem-e-https-na-rede.md)).

### Ativar

1. No `.env`: `COMPOSE_PROFILES=cpu,lan` (ou `gpu,lan`) e `SNOOK_LAN_HOST=<nome ou IP do servidor>`, por exemplo `snook.casa.lan` ou `192.168.0.10`.
2. Manter `SNOOK_BIND=127.0.0.1`. Clientes da rede entram só pelo Caddy, em HTTPS. `SNOOK_BIND=0.0.0.0` junto com `lan` expõe também HTTP sem TLS: não recomendado.
3. `docker compose up -d`.
4. Confiar na CA local em cada cliente (abaixo).
5. Abrir `https://<SNOOK_LAN_HOST>`.

### `SNOOK_LAN_HOST`

- `core/settings.py` lê `SNOOK_LAN_HOST`. Se definido e se `ALLOWED_HOSTS` e `ALLOWED_ORIGINS` não vierem explícitos:
  - `ALLOWED_HOSTS` = `localhost,127.0.0.1,<SNOOK_LAN_HOST>`;
  - `ALLOWED_ORIGINS` = `http://localhost:8080,http://127.0.0.1:8080,https://<SNOOK_LAN_HOST>`.
- Valor validado no startup: nome DNS ou IP, sem esquema, porta ou caminho. Valor inválido impede a subida, com mensagem clara.
- Com perfil `lan` ativo e `SNOOK_LAN_HOST` vazio, o Caddy não sobe (site sem endereço) e o README aponta a variável.
- Compose passa `SNOOK_LAN_HOST` ao `caddy` e ao backend (`backend` e `backend-gpu`).

### Caddyfile mínimo (`deploy/Caddyfile`)

```
{
	admin off
	auto_https disable_redirects
}

{$SNOOK_LAN_HOST} {
	tls internal
	header Strict-Transport-Security "max-age=31536000"
	reverse_proxy frontend:80
}
```

- `tls internal`: Caddy cria CA local e certificado para o nome ou IP.
- HSTS só aqui (SEC-13). Sem `includeSubDomains`. Navegador ignora HSTS quando o host é IP; o HTTPS segue valendo.
- Porta 80 não é publicada; por isso `disable_redirects`.
- `reverse_proxy` mantém o `Host` original e grava `X-Forwarded-For` (descarta o valor vindo do cliente, porque o Caddy não tem `trusted_proxies`) e `X-Forwarded-Proto: https`.

### `X-Forwarded-Proto` e `X-Forwarded-For`

Regra: só proxy confiável define esquema e IP do cliente.

- **Caddy:** grava os dois cabeçalhos, como acima.
- **nginx (`deploy/nginx.conf`):**
  - `X-Forwarded-For`: `$proxy_add_x_forwarded_for` (acrescenta o IP de quem conectou ao nginx).
  - `X-Forwarded-Proto`: repassa o valor só se a conexão vem do Caddy; senão, usa `$scheme`.

    ```
    map "$remote_addr:$http_x_forwarded_proto" $snook_fwd_proto {
        default              $scheme;
        "172.28.0.11:https"  https;
    }
    ```

  - `proxy_set_header Host $host;` e `proxy_set_header X-Forwarded-Proto $snook_fwd_proto;` no `location /api/`.
- **Backend:** confia em `X-Forwarded-*` só quando a conexão vem de um IP de `TRUSTED_PROXY_IPS`.
  - IP do cliente: percorre `X-Forwarded-For` da direita para a esquerda e pega o primeiro IP fora de `TRUSTED_PROXY_IPS`. Um valor forjado pelo cliente fica à esquerda e é ignorado.
  - Esquema: `X-Forwarded-Proto` do nginx.
  - Implementação: `--proxy-headers --forwarded-allow-ips` do uvicorn, se a versão travada no `uv.lock` seguir a regra acima; senão, middleware em `core/http_security.py`. O teste decide.
- **Efeitos verificados:**
  - `SESSION_COOKIE_SECURE=auto` liga `Secure` quando o esquema é `https` (perfil `lan`) e em `localhost` (ADR-0008, SEC-03).
  - Limite de login por IP (ADR-0010) conta o IP do cliente da rede, não o IP do Caddy nem do nginx.
- **Testes do resolvedor de proxy (Task 7; checkpoint Fundação):** direto na função do resolvedor ou por rota de teste que devolve IP e esquema resolvidos. A rota de teste é registrada só na suíte do Pytest, nunca na app de produção.
  - conexão de IP em `TRUSTED_PROXY_IPS` com `X-Forwarded-For: 1.2.3.4, <IP do cliente>`: IP resolvido é `<IP do cliente>`;
  - `X-Forwarded-Proto: https` vale só vindo de IP em `TRUSTED_PROXY_IPS`;
  - conexão de IP fora de `TRUSTED_PROXY_IPS`: cabeçalhos ignorados; valem IP e esquema da conexão.
- **Testes de HTTPS (Task 6b; checkpoint Fundação):** `https://<SNOOK_LAN_HOST>` responde e traz HSTS (ver "Verificação manual").
- **Testes de cookie e limitador (Tasks 10 e 11; checkpoint `auth`):** precisam de login e limitador prontos.
  - login pelo Caddy: cookie com `Secure`; limitador vê o IP do cliente;
  - requisição direta ao nginx com `X-Forwarded-For: 1.2.3.4` e `X-Forwarded-Proto: https` forjados: limitador vê o IP real; esquema `http`.

### Confiar na CA local

A CA fica no volume `caddy-data`. A chave privada da CA assina certificado para qualquer nome nos clientes que confiam nela: trate `caddy-data` como segredo.

1. Exportar o certificado raiz (só o público):
   `docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./snook-lan-ca.crt`
2. Copiar `snook-lan-ca.crt` para cada cliente.
3. Instalar no cliente:
   - Fedora e outros com `ca-trust`: `sudo cp snook-lan-ca.crt /etc/pki/ca-trust/source/anchors/` e depois `sudo update-ca-trust`.
   - Chrome e Edge no Linux também leem o NSS do usuário: `certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "Snook LAN CA" -i snook-lan-ca.crt` (pacote `nss-tools`).
   - Windows (terminal como administrador): `certutil -addstore -f Root snook-lan-ca.crt`.
   - macOS: `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain snook-lan-ca.crt`.
4. Reiniciar o navegador.
5. Conferir: `https://<SNOOK_LAN_HOST>` abre sem alerta; o botão "Gravar reunião" fica habilitado (`screen-recording` critério 28).
6. Ao desativar o perfil `lan` ou trocar de servidor, remover a CA dos clientes.

### Verificação manual

- Checkpoint Fundação (Task 6b): `curl --cacert snook-lan-ca.crt -sI https://<SNOOK_LAN_HOST>/` responde por HTTPS e mostra `Strict-Transport-Security`.
- Checkpoint `auth` (Tasks 10 e 11): login pela rede devolve `Set-Cookie` com `Secure`; falhas de login pela rede contam o IP do cliente.
- Checkpoint `screen-recording` (Tasks 28 e 29): critério transversal 22, gravação de tela funciona num cliente da rede que confia na CA; checklist manual em Chrome e Edge no Windows e no Fedora.

## CLI de escrita (`delete-user`, `rotate-master-key`)

Comandos que escrevem no banco rodam com o backend parado. A trava `/data/snook.lock` garante isso (ADR-0006).

1. `docker compose stop backend backend-gpu` (para o serviço do perfil ativo; o outro é ignorado). A Task 6 confere que o comando funciona com um dos serviços fora do perfil ativo. Se não funcionar, este passo vira um comando por perfil: `docker compose stop backend` (CPU) e `docker compose stop backend-gpu` (GPU).
2. Perfil CPU: `docker compose run --rm backend python -m snook.cli delete-user <username>`.
   Perfil GPU: `docker compose run --rm backend-gpu python -m snook.cli delete-user <username>`.
3. `docker compose up -d`.

- Backend no ar: o comando acha a trava ocupada, para com erro e não escreve nada.
- `delete-user` pede que o Operador digite o nome de usuário de novo, ou aceita `--yes`. Confirmação diferente do argumento: o comando sai sem apagar nada (SEC-24; teste no checkpoint `delete-user`).
- Dado apagado pode seguir no último `snook.db.bak-*` até a próxima migração (`03-security.md`, "Backups").

## CI/CD ([ADR-0017](adrs/0017-ferramentas-e-ci.md))

`.github/workflows/ci.yml`, em `pull_request` para `develop` e `main` e em `push` para `develop`:

| Job | Passos |
|---|---|
| `backend` | `uv sync --frozen`; `ruff check`; `ruff format --check`; `mypy src`; `lint-imports`; `pytest`; `pip-audit` |
| `frontend` | `npm ci --ignore-scripts`; `npm run lint`; `npm run typecheck`; `npm test -- --run`; `npm run build`; `npm audit --omit=dev` |
| `secrets` | `gitleaks detect` no diff; checagem de que `.gitignore` cobre `.env`, `*.db`, `audios/` |
| `images` | `docker compose build` (perfil `cpu`), sem push |

- Suítes `models_real` e `llm_real` não rodam no CI. Rodam à mão antes da release, com registro no PR de release.
- Sem CD: sem registro de imagens. Release = tag `vX.Y.Z` em `main` (GitFlow). Usuário faz `git pull` e `docker compose up -d --build`.
- Branch protection sugerida: `develop` e `main` exigem CI verde.

## Segredos

- Só no `.env` do host. Nunca em imagem, `compose.yaml` versionado ou log.
- Volume `caddy-data` guarda a chave privada da CA local: fora de backup compartilhado e do git.
- CI não usa segredo real. Testes usam chave-mestra gerada no `conftest.py`.
- Segredo vazado em commit: girar primeiro (nova chave-mestra com rotação; novo `HF_TOKEN`), depois limpar histórico.

## Rollback

1. `git checkout <tag anterior>`.
2. Se a versão nova rodou migração: parar o backend, restaurar o backup.
   - `docker compose stop backend backend-gpu` (mesma conferência da Task 6 descrita em "CLI de escrita"; se falhar, use o comando do perfil ativo)
   - `docker compose run --rm --entrypoint sh backend -c "cp /data/snook.db.bak-<rev> /data/snook.db"` (no perfil GPU, troque `backend` por `backend-gpu`)
3. `docker compose up -d --build`.

- Migração só para frente. Backup antes de migrar é feito pelo startup (ADR-0006).
- Arquivos em `./audios` não mudam de formato entre versões. Mudança de formato exige ADR novo.
