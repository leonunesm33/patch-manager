export const dashboardMetrics = [
  {
    label: "Maquinas monitoradas",
    value: "27",
    detail: "19 online e 8 em manutencao",
    tone: "#00d4ff",
  },
  {
    label: "Patches pendentes",
    value: "43",
    detail: "7 criticos aguardando aprovacao",
    tone: "#ffc542",
  },
  {
    label: "Conformidade",
    value: "94%",
    detail: "janela dos ultimos 30 dias",
    tone: "#00e5a0",
  },
  {
    label: "Falhas recentes",
    value: "12",
    detail: "necessitam reprocessamento",
    tone: "#ff4d6a",
  },
];

export const weeklyPatchVolume = [
  { label: "03/Abr", windows: 8, linux: 3 },
  { label: "04/Abr", windows: 5, linux: 2 },
  { label: "05/Abr", windows: 12, linux: 6 },
  { label: "06/Abr", windows: 3, linux: 1 },
  { label: "07/Abr", windows: 9, linux: 4 },
  { label: "08/Abr", windows: 14, linux: 5 },
  { label: "09/Abr", windows: 7, linux: 5 },
];

export const activityFeed = [
  {
    title: "KB5034441 aprovado para servidores web",
    detail: "Scope: Windows Server Production",
    status: "ok",
  },
  {
    title: "ubuntu-prod-03 reportou atualizacoes criticas",
    detail: "2 pacotes aguardando janela de manutencao",
    status: "warn",
  },
  {
    title: "SRV-DB-02 falhou ao aplicar KB5034122",
    detail: "Erro de reboot pendente identificado",
    status: "error",
  },
];
