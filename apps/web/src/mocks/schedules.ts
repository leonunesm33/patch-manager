export const schedules = [
  {
    id: "sched-1",
    name: "Janela Semanal Linux",
    scope: "Ubuntu Production",
    cronLabel: "Toda quarta, 02:00",
    rebootPolicy: "Somente se necessario",
  },
  {
    id: "sched-2",
    name: "Patches Criticos Windows",
    scope: "Windows Servers",
    cronLabel: "Diariamente, 03:00",
    rebootPolicy: "Sempre reiniciar",
  },
];
