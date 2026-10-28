export const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  deepseek: "DeepSeek",
  ollama: "Ollama",
}

export const MESSAGES = {
  title: "Nomear participantes",
  description:
    "Ouça a amostra de cada voz e digite o nome da pessoa. Vozes com o mesmo nome viram um só participante.",
  back: "Voltar à reunião",
  loading: "Carregando…",
  notFound: "Reunião não encontrada.",
  notAvailable:
    "Esta reunião não está esperando nomes. Os nomes só são dados depois da transcrição, uma vez.",
  speakersLabel: "Vozes da reunião",
  namePrefix: "Nome de ",
  speechTime: "Tempo de fala",
  play: (label: string) => `Ouvir amostra de ${label}`,
  pause: (label: string) => `Pausar amostra de ${label}`,
  sampleError: "Não foi possível tocar a amostra.",
  mergedWith: (labels: string[]) =>
    `Mesmo nome de ${labels.join(", ")}: serão juntados num só participante.`,
  summary: (speakers: number, participants: number) =>
    `${speakers} ${speakers === 1 ? "voz" : "vozes"}, ${participants} ${participants === 1 ? "participante" : "participantes"}`,
  providerTitle: "Geração do backlog",
  providerUsed: (provider: string, model: string) =>
    `Usará ${provider}, modelo ${model}.`,
  noProvider: "Nenhum provedor de LLM ativo. Ative um para confirmar.",
  openSettings: "Abrir configurações",
  missingNames: "Dê um nome a cada voz para confirmar.",
  confirm: "Confirmar nomes",
  confirming: "Confirmando…",
}
