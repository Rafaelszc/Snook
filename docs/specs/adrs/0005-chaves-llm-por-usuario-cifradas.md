# ADR-0005: Chaves de LLM por Usuário, cifradas no SQLite

- Status: Aceita
- Data: 2026-10-22
- Fonte: Q15, Q21 (substituída), Q22, Q33, Q51, Q64; RT-02.

## Contexto

Cada Usuário paga o próprio uso de LLM. Chave vazada gasta na conta dele.

## Decisão

- Configuração de LLM por Usuário, no SQLite.
- Chave cifrada com chave-mestra que vem só do `.env`.
- Depois de salva, a chave volta à UI só como máscara (3 primeiros e 4 últimos caracteres; chave com menos de 12 caracteres vira `...`).
- Chave decifrada existe só dentro de `llm-providers`, no momento da chamada.
- Remover configuração apaga a chave cifrada.

## Consequências

- Algoritmo, nome da variável, rotação e perda da chave-mestra: ADR-0009.
- Backup do volume do SQLite sem a chave-mestra não expõe chaves.
