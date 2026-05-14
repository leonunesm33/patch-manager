export function getUserInitials(name: string, override?: string | null) {
  if (override?.trim()) return override.trim().slice(0, 4).toUpperCase();

  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 0) return "US";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export function getRoleLabel(role: string) {
  if (role === "admin") return "Administrador";
  if (role === "user") return "Usuario";
  return role;
}
