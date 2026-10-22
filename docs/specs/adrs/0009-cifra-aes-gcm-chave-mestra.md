# ADR-0009: Cifra das chaves de LLM com AES-256-GCM e chave-mestra `SNOOK_MASTER_KEY`

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q4 da rodada de decisões do planner: AES-256-GCM com o tratamento de perda da chave-mestra descrito abaixo. Recomendação aceita sem mudança.

## Contexto

- ADR-0005 (Aceita) exige chave cifrada com chave-mestra do `.env`.
- Spec deixava aberto: algoritmo, nome da variável, troca da chave-mestra e perda dela. Resolvido por este ADR.

## Opções consideradas

1. **AES-256-GCM (`cryptography`), nonce aleatório de 96 bits, AAD com `user_id` e `provider`, identificador de versão da chave.**
   - Prós: cifra autenticada; AAD impede trocar o valor cifrado de uma linha para outra; rotação por versão.
   - Contras: código de nonce e versão a manter.
2. **Fernet / `MultiFernet` (`cryptography`).**
   - Prós: API simples; rotação pronta com `MultiFernet.rotate`.
   - Contras: AES-128-CBC + HMAC; sem AAD.
3. **SQLCipher (banco inteiro cifrado).**
   - Prós: cifra tudo, inclusive transcrições.
   - Contras: binário nativo extra; chave em todo acesso; não atende "só a chave cifrada" melhor que a opção 1.

## Decisão

Opção 1.

- Variável `SNOOK_MASTER_KEY`: 32 bytes em base64 url-safe. `.env.example` traz comando para gerar: `python -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`.
- Variável opcional `SNOOK_MASTER_KEY_PREVIOUS`: chave anterior, só para decifrar durante a rotação.
- Formato gravado: `key_version` (1 byte lógico, coluna própria), `nonce` (12 bytes), `ciphertext` (inclui tag). AAD: `snook:llm-key:v1:<user_id>:<provider>`.
- Backend não sobe sem `SNOOK_MASTER_KEY` válida (falha rápida com mensagem que não mostra o valor).
- Rotação: comando `python -m snook.cli rotate-master-key` decifra com a anterior e recifra com a atual, numa transação.
- Chave-mestra perdida ou trocada sem rotação: decifrar falha. Configuração fica com `key_status = unreadable`. Tela mostra "chave ilegível, informe a chave de novo". "Gerar" devolve o erro tipado "credencial recusada" com essa mensagem. Nada é apagado sozinho.

## Consequências

- Backup do volume sem a chave-mestra não expõe chaves.
- Perder a chave-mestra obriga cada Usuário a redigitar a chave. Documentar no README.
