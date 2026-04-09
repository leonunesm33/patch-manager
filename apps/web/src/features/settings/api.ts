import { http } from "@/lib/http";
import type { SettingsResponse } from "@/features/settings/types";

export function fetchSettings() {
  return http<SettingsResponse>("/settings");
}
