export const MESSAGES = {
  // `screen-recording` 27; vence `unsupported`.
  insecure:
    "A gravação exige HTTPS ou localhost. O Operador pode ativar o perfil lan. O envio de arquivo continua disponível.",
  // `screen-recording` 22.
  unsupported:
    "A gravação funciona só no Chrome ou Edge. O envio de arquivo continua disponível.",
  // `screen-recording` 23; aviso, não bloqueia.
  unofficial:
    "O suporte oficial à gravação é só do Chrome e do Edge. A gravação pode falhar neste navegador.",
  // `screen-recording` 4 a 7.
  missingTitle: "Falta uma fonte de áudio",
  missingDisplay:
    "O som da tela não está disponível. Compartilhe uma aba ou tela com áudio, ou grave só com o microfone.",
  missingMic:
    "O microfone não está disponível ou o acesso foi negado. Grave só com o som da tela ou cancele.",
  micOnly: "Gravar só com o microfone",
  displayOnly: "Gravar só com o som da tela",
  cancel: "Cancelar",
  noSource:
    "Nenhuma fonte de áudio disponível. Compartilhe uma aba ou tela com áudio, ou permita o microfone.",
  recordFailed:
    "Não foi possível iniciar a gravação. Tente de novo ou envie um arquivo.",
  // `screen-recording` 8, 10 a 12.
  panel: "Gravação em andamento",
  recording: "Gravando",
  elapsed: "Tempo decorrido",
  stop: "Parar",
  stopping: "Parando…",
  limitReached:
    "A gravação parou sozinha em 1h59m50s, o limite. Envie o que foi gravado.",
  leaveConfirm:
    "A gravação ainda não foi enviada e será perdida. Sair mesmo assim?",
} as const
