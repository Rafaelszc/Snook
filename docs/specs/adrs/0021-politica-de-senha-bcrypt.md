# ADR-0021: Custo do bcrypt e tamanho máximo da senha

- Status: Aceita
- Data: 2026-10-22 (proposta e aceite)
- Fonte: decisão do usuário em 2026-10-22, Q16 da rodada de decisões do planner: bcrypt custo 12, senha até 72 bytes, acima disso HTTP 422. Recomendação aceita sem mudança.

## Contexto

- Q2: senha só como hash bcrypt. Q20: mínimo de 8 caracteres.
- bcrypt usa só os primeiros 72 bytes. Senha maior seria truncada em silêncio.
- Testes precisam de bcrypt rápido.

## Opções consideradas

1. **Custo 12; senha acima de 72 bytes UTF-8 recusada com HTTP 422.**
   - Prós: sem truncamento silencioso; comportamento previsível.
   - Contras: frase-senha muito longa recusada.
2. **Custo 12; pré-hash SHA-256 + base64 antes do bcrypt.**
   - Prós: aceita qualquer tamanho.
   - Contras: desvio da decisão "hash bcrypt" (Q2); critério 9 do `auth` (`bcrypt.checkpw` com a senha original) falharia.
3. **Custo 10.**
   - Prós: login mais rápido.
   - Contras: abaixo do mínimo recomendado (12).

## Decisão

Opção 1.

- `BCRYPT_ROUNDS=12` em produção; `4` nos testes, por configuração.
- Senha: de 8 caracteres a 72 bytes em UTF-8. Mensagem: "senha com no máximo 72 bytes".
- Login com identificador inexistente roda `bcrypt.checkpw` contra hash fixo, para tempo igual ao de senha errada.
- Mensagem de login com falha única: "email, nome de usuário ou senha inválidos".

## Consequências

- Critério novo no PRD `auth` (senha acima de 72 bytes recusada com HTTP 422): aprovado pelo usuário em 2026-10-22, entre as mudanças no spec. Aplicado em `01-prd/auth.md` (critério 28).
