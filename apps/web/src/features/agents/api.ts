import { http } from "@/lib/http";
import type { AgentInventoryDetail } from "@/features/agents/types";

export function fetchAgentInventoryDetail(agentId: string) {
  return http<AgentInventoryDetail>(`/agents/inventory-details/${agentId}`);
}
