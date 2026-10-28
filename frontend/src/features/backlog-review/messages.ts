import { STATUS_LABELS, type Status } from "@/components/surfaces/messages"

export const MESSAGES = {
  title: "Revisão do backlog",
  back: "Voltar à reunião",
  loading: "Carregando backlog…",
  notFound: "Reunião não encontrada.",
  noBacklog: "Esta reunião ainda não tem backlog.",
  empty: "Nenhuma User Story nesta geração.",
  emptyHint: "Crie uma Epic para começar a escrever User Stories.",
  readOnly: (status: Status) =>
    `Backlog anterior, só para leitura. Situação atual: ${STATUS_LABELS[status]}.`,
  failed: "A última geração falhou. O backlog anterior está só para leitura.",
  retry: "Tentar novamente",
  retrying: "Tentando…",
  retryTitle: "Tentar a geração de novo?",
  retryDescription:
    "Se a nova geração terminar bem, ela substitui este backlog e todas as edições feitas nele se perdem.",
  retryConfirm: "Tentar novamente",
  epics: (count: number) => (count === 1 ? "1 Epic" : `${count} Epics`),
  stories: (count: number) =>
    count === 1 ? "1 User Story" : `${count} User Stories`,
  // Epic
  epic: "Epic",
  epicName: "Nome da Epic",
  newEpic: "Nova Epic",
  createEpic: "Criar Epic",
  toggleEpic: (name: string, open: boolean) =>
    `${open ? "Recolher" : "Expandir"} Epic ${name}`,
  deleteEpic: "Excluir Epic",
  deleteEpicTitle: (name: string) => `Excluir a Epic "${name}"?`,
  deleteEpicDescription:
    "A Epic sai do backlog. Esta ação não pode ser desfeita.",
  deleteEpicBlocked: "Só é possível excluir uma Epic sem User Stories.",
  mergeEpic: (name: string) =>
    `Já existe a Epic "${name}". Ao salvar, as duas serão juntadas.`,
  // User Story
  storyName: "Nome da User Story",
  asA: "Como",
  iWant: "Eu quero",
  soThat: "Para",
  priority: "Prioridade",
  storyPoints: "Story Points",
  requester: "Solicitante",
  noRequester: "Sem solicitante",
  requestedAt: "Quando",
  requestedAtHint: "hh:mm:ss, vazio se não souber.",
  newStory: "Nova User Story",
  createStory: "Criar User Story",
  moveStory: "Mover",
  moveTitle: (usId: string) => `Mover ${usId} para outra Epic`,
  moveTarget: "Epic de destino",
  moveConfirm: "Mover",
  deleteStory: "Excluir User Story",
  deleteStoryTitle: (usId: string) => `Excluir ${usId}?`,
  deleteStoryDescription:
    "A User Story e os critérios dela saem do backlog. O US-id não é reaproveitado.",
  // Critérios
  criteria: "Critérios de aceitação",
  given: "Dado",
  when: "Quando",
  then: "Então",
  newCriterion: "Adicionar critério",
  createCriterion: "Adicionar",
  deleteCriterion: "Excluir critério",
  deleteCriterionTitle: "Excluir este critério?",
  deleteCriterionDescription: "O critério sai da User Story.",
  lastCriterion: "Toda User Story precisa de pelo menos um critério de aceite.",
  // Edição
  edit: (label: string) => `Editar ${label}`,
  save: "Salvar",
  saving: "Salvando…",
  cancel: "Cancelar",
  delete: "Excluir",
  // Ações da Reunião
  regenerate: "Regenerar",
  regenerating: "Regenerando…",
  regenerateTitle: "Regenerar o backlog?",
  regenerateDescription:
    "A LLM gera um backlog novo. Se terminar bem, ele substitui este e todas as edições feitas aqui se perdem.",
  regenerateSplit:
    "Esta reunião foi dividida em partes. Use os mesmos cortes ou reajuste antes de gerar.",
  checkingSplit: "Verificando a divisão…",
  sameCuts: "Mesmos cortes",
  adjustCuts: "Reajustar cortes",
  exportMd: "Exportar Markdown",
  exportJson: "Exportar JSON",
  renameParticipant: "Renomear participante",
  participant: "Participante",
  newName: "Novo nome",
  renameConfirm: "Renomear",
  mergeParticipant: (name: string) =>
    `Já existe o participante "${name}". Ao salvar, os dois serão unidos e as User Stories passam para ele.`,
}
