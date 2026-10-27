export const MESSAGES = {
  // `screen-recording` 1, 2, 26.
  record: "Gravar reunião",
  recordTitle: "Gravar reunião",
  recordDescription:
    "Grava o som da aba da chamada e o seu microfone. Só o áudio fica guardado.",
  recordHowTo:
    "Ao começar, escolha a aba da reunião e marque o compartilhamento de áudio. Depois permita o microfone.",
  keepOpen: "Mantenha esta página aberta até enviar a gravação.",
  uploadInstead: "Enviar arquivo",
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
  // `screen-recording` 14 a 20; rótulos iguais aos do upload.
  sendTitle: "Enviar gravação",
  sendDescription:
    "Confira o título e envie. A transcrição roda neste servidor, em português.",
  title: "Título",
  titleHint: "Preenchido com o nome do arquivo. Pode mudar.",
  speakers: "Número de participantes",
  speakersHint: "Opcional, de 1 a 20. Ajuda a separar as vozes.",
  send: "Enviar",
  sending: "Enviando…",
  progress: "Progresso do envio",
  networkError:
    "Sem conexão com o servidor. A gravação continua nesta página: tente de novo.",
  retry: "Tentar de novo",
} as const
