export const settingsGroups = {
  policy: [
    {
      label: "Patches criticos automaticos",
      description: "Aplica patches criticos sem aprovacao manual.",
      enabled: true,
    },
    {
      label: "Patches opcionais requerem aprovacao",
      description: "Mantem o time no controle sobre updates nao obrigatorios.",
      enabled: true,
    },
  ],
  notifications: [
    {
      label: "Notificar falhas",
      description: "Envia alerta imediato quando uma execucao falha.",
      enabled: true,
    },
    {
      label: "Relatorio semanal",
      description: "Entrega uma visao executiva de conformidade.",
      enabled: false,
    },
  ],
};
