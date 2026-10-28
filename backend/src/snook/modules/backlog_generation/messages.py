# Motivo de resposta inválida: texto fixo, nunca trecho da resposta da LLM (SEC-18).
RESPONSE_NOT_JSON = "a resposta do modelo não veio em JSON"
RESPONSE_OFF_SCHEMA = "a resposta do modelo não segue o formato do backlog"
REQUESTED_AT_OUT_OF_RANGE = "a resposta do modelo cita um instante fora da duração do áudio"

NO_ACTIVE_PROVIDER = "Nenhum provedor de LLM ativo. Ative um em Configurações para continuar."
INVALID_RESPONSE = "A resposta do modelo para a Parte {index} é inválida: {reason}."
GENERATION_FAILED = "Falha ao gerar o backlog no provedor de LLM. Tente novamente."
UNEXPECTED = "Falha inesperada ao gerar o backlog."

# Uma por erro tipado de "Gerar" (`backlog-generation` 26). Nunca leva a chave (SEC-07).
CREDENTIAL_REJECTED = "O provedor de LLM recusou a chave. Confira a chave em Configurações."
KEY_UNREADABLE = "A chave do provedor de LLM está ilegível. Informe de novo em Configurações."
PROVIDER_UNREACHABLE = "O provedor de LLM está inacessível. Confira a conexão e tente novamente."
MODEL_NOT_FOUND = "O modelo configurado não existe no provedor de LLM. Troque em Configurações."
CONTEXT_LIMIT_EXCEEDED = (
    "A Parte {index} passou do limite de contexto do modelo. Divida de novo ou troque de modelo."
)
PROVIDER_RATE_LIMITED = "Limite de uso do provedor de LLM atingido. Aguarde e tente novamente."
PART_TOO_LARGE = (
    "A Parte {index} não cabe no modelo configurado. Divida de novo ou troque de modelo."
)
