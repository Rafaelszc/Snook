# Snook

Recebe gravação de reunião, diariza e transcreve localmente em pt-BR. LLM do Usuário gera Epics e User Stories. Uso só local: máquina do usuário ou rede confiável.

Specs em `docs/specs/`. Regras para agentes em `AGENTS.md`.

## Requisitos

- Docker com Compose v2.
- GPU (opcional): driver NVIDIA e NVIDIA Container Toolkit.
- Conta no HuggingFace com os termos do Pyannote aceitos.

## Primeira execução

1. `cp .env.example .env`.
2. Preencher `SNOOK_MASTER_KEY` (comando no `.env.example`) e `HF_TOKEN`.
3. Aceitar no HuggingFace, com a conta do `HF_TOKEN`, os termos de `pyannote/speaker-diarization-3.1` e `pyannote/segmentation-3.0`. Sem o aceite, a diarização falha.
4. `mkdir -p audios` (precisa ser gravável pelo UID 1000).
5. `docker compose up -d --build`.
6. Opcional: `docker compose exec backend python -m snook.cli download-models` (GPU: `backend-gpu`). Senão, baixa na primeira transcrição.
7. Abrir `http://localhost:8080`, criar conta e cadastrar o provedor de LLM em Configurações.

GPU: `COMPOSE_PROFILES=gpu` no `.env`.

## Ollama

- URL padrão: `http://host.docker.internal:11434`. Aponta para o Ollama rodando no host, visto de dentro do container (`extra_hosts: host-gateway` no `compose.yaml`).
- `localhost` não serve: dentro do container é o próprio container.
- No Linux, o Ollama precisa escutar fora do loopback para o container alcançar: `OLLAMA_HOST=0.0.0.0` no serviço do Ollama.
- Ollama em outra máquina: usar a URL dela (`http://192.168.0.20:11434`). Só `http` ou `https`; redirecionamento não é seguido.
- Conferir de dentro do container: `docker compose exec backend python -c "import httpx; print(httpx.get('http://host.docker.internal:11434/api/tags').status_code)"` imprime `200`.

## Rede confiável (perfil `lan`)

HTTPS para outros computadores da rede, com CA local do Caddy. Detalhe em `docs/specs/08-deployment.md`, "Perfil lan".

1. No `.env`: `COMPOSE_PROFILES=cpu,lan` (ou `gpu,lan`) e `SNOOK_LAN_HOST=<nome ou IP do servidor>`, ex.: `192.168.0.10`.
2. Manter `SNOOK_BIND=127.0.0.1`: a rede entra só pelo Caddy, em HTTPS.
3. `docker compose up -d`.
4. Exportar a CA (só o certificado público): `docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./snook-lan-ca.crt`.
5. Instalar `snook-lan-ca.crt` em cada cliente:
   - Fedora: `sudo cp snook-lan-ca.crt /etc/pki/ca-trust/source/anchors/ && sudo update-ca-trust`; Chrome e Edge no Linux também: `certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "Snook LAN CA" -i snook-lan-ca.crt`.
   - Windows (administrador): `certutil -addstore -f Root snook-lan-ca.crt`.
   - macOS: `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain snook-lan-ca.crt`.
6. Reiniciar o navegador e abrir `https://<SNOOK_LAN_HOST>`. "Gravar reunião" só funciona em HTTPS ou `localhost`.

- `SNOOK_LAN_HOST` vazio com `lan` ativo: o Caddy não sobe.
- O volume `caddy-data` guarda a chave privada da CA. Trate como segredo. Ao desligar o perfil ou trocar de servidor, remova a CA dos clientes.

## Modelos

- Whisper `large-v3-turbo` e Pyannote `speaker-diarization-3.1`, em revisão fixa (hash de commit em `WHISPER_REVISION` e `PYANNOTE_REVISION`; SEC-22).
- Baixar antes (opcional; senão baixa na primeira transcrição): `docker compose exec backend python -m snook.cli download-models` (GPU: `backend-gpu`). Cache no volume `snook-models`; a segunda execução não baixa de novo.
- Sem rede depois do download: `MODELS_OFFLINE=true` no `.env` e `docker compose up -d`.
- Trocar `WHISPER_MODEL` pede trocar `WHISPER_REVISION` junto.

## Dados

- Banco e modelos: volumes `snook-db` e `snook-models`. `docker compose down` mantém; `docker compose down -v` apaga.
- Áudios: `./audios`, fora do git.
- `.env` guarda segredos. Nunca commitar.

### Backup antes de migração

- Ao subir com migração nova, o backend copia o banco para `/data/snook.db.bak-<revisão>` no volume `snook-db`. Fica só a última cópia.
- Dado apagado (Reunião excluída ou `delete-user`) pode seguir nessa cópia até a próxima migração.
- Ver e apagar a cópia:

  ```
  docker compose exec backend sh -c 'ls -l /data/snook.db.bak-*'
  docker compose exec backend sh -c 'rm -f /data/snook.db.bak-*'
  ```

  (GPU: `backend-gpu`.)
- O app não faz outro backup. Para guardar uma cópia: pare o backend e copie o volume `snook-db`. Backup sem a `SNOOK_MASTER_KEY` não expõe chaves de LLM.

## Excluir um Usuário

Só pelo Operador, com o backend parado (a trava `/data/snook.lock` impede rodar com ele no ar).

1. `docker compose stop backend backend-gpu`.
2. `docker compose run --rm backend python -m snook.cli delete-user <username>` (GPU: `backend-gpu`).
3. Digitar o nome de usuário de novo para confirmar, ou passar `--yes`.
4. `docker compose up -d`.

Apaga o Usuário, sessões, configurações de LLM, Reuniões, backlogs e os diretórios em `./audios`. Depois, apague também o backup de migração (acima).

## Chave-mestra (`SNOOK_MASTER_KEY`)

Cifra as chaves de LLM dos Usuários (ADR-0009). Backup do banco sem ela não expõe chaves.

Trocar a chave-mestra:

1. No `.env`: chave atual vai para `SNOOK_MASTER_KEY_PREVIOUS`; nova em `SNOOK_MASTER_KEY`.
2. `docker compose stop backend backend-gpu`.
3. `docker compose run --rm backend python -m snook.cli rotate-master-key` (GPU: `backend-gpu`).
4. Conferir a saída. Apagar `SNOOK_MASTER_KEY_PREVIOUS` do `.env` e o backup `snook.db.bak-rotate` do volume.
5. `docker compose up -d`.

Chave-mestra perdida ou trocada sem rotação: chaves ficam ilegíveis. Nada é apagado. Cada Usuário informa a chave de novo em Configurações.

## Desempenho medido

Sem meta de tempo na v1. Números do spike da Task 1 (faster-whisper `large-v3-turbo` int8 e Pyannote 3.1 em CPU, áudio de 10 min):

| Etapa | Tempo | CPU | RAM |
|---|---|---|---|
| Transcrição (faster-whisper) | a medir | a medir | a medir |
| Diarização (Pyannote) | a medir | a medir | a medir |

## Desenvolvimento

Comandos de teste e lint em `AGENTS.md`, "Comandos".

- `uv sync` sem extra não instala torch, faster-whisper nem pyannote: testes padrão e CI usam engines falsas.
- Suíte `models_real` (à mão, antes da release): `cd backend && uv sync --extra cpu && uv run pytest -m models_real`. Lê `HF_TOKEN` do `.env`; cache em `MODELS_REAL_ROOT` (padrão `~/.cache/snook/models`). Teste do pipeline pede `ffmpeg` no host.
- Fixture de voz da suíte: `backend/tests/fixtures/audio/two_voices.py` (espeak-ng, vozes sintéticas).

## Checklist de release

Rodar antes de abrir o PR `release/*` → `main`. Resultado de cada item vai na descrição do PR.

1. Gates: `cd backend && uv run pytest && uv run ruff check . && uv run mypy src && uv run lint-imports && uv run pip-audit`; `cd frontend && npm ci --ignore-scripts && npm test -- --run && npm run build && node scripts/check-bundle-size.mjs && npm audit --omit=dev`. Testes com `ffmpeg` pulam no host sem ele; rodam no CI.
2. Auditorias: `pip-audit` e `npm audit --omit=dev` sem crítico ou alto alcançável (SEC-21). `npm audit signatures` sem pacote sem atestado.
3. Tabela "Verificação" de `docs/specs/03-security.md`: SEC-01 a SEC-27, um resultado por item.
4. Docker (SEC-23): `docker compose exec backend id -u` imprime `1000`; `docker compose ps` sem porta do backend.
5. Perfil `lan` (SEC-13, SEC-27): `curl --cacert snook-lan-ca.crt -sI https://<SNOOK_LAN_HOST>/` mostra `Strict-Transport-Security`.
6. Persistência (critério transversal 2): `docker compose down` sem `-v`, depois `up`; Reuniões e `./audios` continuam.
7. Suítes opcionais: `uv run pytest -m models_real` (pede `HF_TOKEN`) e `uv run pytest -m llm_real` (lê a chave de cada provedor do ambiente ou do `.env`; provedor sem chave pula).
