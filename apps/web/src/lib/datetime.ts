const SAO_PAULO_TIME_ZONE = "America/Sao_Paulo";

function parseDate(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTimeSaoPaulo(value: string | Date) {
  const date = parseDate(value);
  if (!date) return typeof value === "string" ? value : "";
  return date.toLocaleString("pt-BR", {
    timeZone: SAO_PAULO_TIME_ZONE,
  });
}

export function formatTimeSaoPaulo(value: string | Date) {
  const date = parseDate(value);
  if (!date) return typeof value === "string" ? value : "";
  return date.toLocaleTimeString("pt-BR", {
    timeZone: SAO_PAULO_TIME_ZONE,
  });
}
