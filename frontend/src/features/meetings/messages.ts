// Iguais às mensagens da API (`meetings` 37; backend `meetings/messages.py`).
export const UNSUPPORTED_FORMAT =
  "Formato não aceito. Use mp3, wav, m4a, ogg, webm ou mp4."
export const TOO_LARGE = "O arquivo passa de 500 MB, o limite de tamanho."
export const EMPTY_FILE = "O arquivo está vazio."

export const STAGE_LABELS = {
  transcription: "Transcrição",
  generation: "Geração do backlog",
} as const

export const MESSAGES = {
  openTranscript: "Ver transcrição",
  nameParticipants: "Nomear participantes",
  nameParticipantsHint:
    "A transcrição terminou. Dê um nome a cada voz para gerar o backlog.",
  listTitle: "Reuniões",
  listDescription: "Gravações enviadas e o andamento de cada uma.",
  newMeeting: "Nova reunião",
  // Entrada da gravação (`screen-recording` 1); a tela mora em `screen-recording`.
  recordMeeting: "Gravar reunião",
  empty: "Nenhuma reunião ainda.",
  emptyHint: "Envie a gravação de uma reunião para começar.",
  loading: "Carregando…",
  loadError: "Não foi possível carregar as reuniões.",
  uploadTitle: "Nova reunião",
  uploadDescription:
    "Envie a gravação. A transcrição roda neste servidor, em português.",
  dropTitle: "Arraste o arquivo ou clique para escolher",
  dropHint: "mp3, wav, m4a, ogg, webm ou mp4, até 500 MB e 2 horas.",
  chosen: "Arquivo escolhido",
  file: "Arquivo da reunião",
  title: "Título",
  titleHint: "Preenchido com o nome do arquivo. Pode mudar.",
  speakers: "Número de participantes",
  speakersHint: "Opcional, de 1 a 20. Ajuda a separar as vozes.",
  send: "Enviar",
  sending: "Enviando…",
  progress: "Progresso do envio",
  fileRequired: "Escolha o arquivo da reunião.",
  createdAt: "Criada em",
  duration: "Duração",
  originalFilename: "Arquivo",
  expectedSpeakers: "Participantes informados",
  notSet: "—",
  back: "Reuniões",
  failedAt: (stage: string) => `Falhou na etapa: ${stage}`,
  editTitle: "Editar título",
  saveTitle: "Salvar",
  savingTitle: "Salvando…",
  cancel: "Cancelar",
  titleSaved: "Título salvo.",
  retry: "Tentar novamente",
  retrying: "Tentando…",
  retryTitle: "Tentar novamente?",
  retryDescription:
    "Se a nova geração terminar bem, o backlog atual é substituído e as edições manuais se perdem.",
  retryConfirm: "Tentar novamente",
  remove: "Excluir",
  removeTitle: "Excluir reunião?",
  removeDescription:
    "O áudio, a transcrição e o backlog desta reunião serão apagados. Não dá para desfazer.",
  removeConfirm: "Excluir reunião",
  notFound: "Reunião não encontrada.",
}
