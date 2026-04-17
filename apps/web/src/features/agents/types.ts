export type AgentInventoryDetailItem = {
  identifier: string;
  title: string;
  current_version: string | null;
  target_version: string | null;
  source: string | null;
  summary: string | null;
  kb_id: string | null;
  security_only: boolean;
  installed_at: string | null;
};

export type AgentInventoryDetail = {
  agent_id: string;
  platform: string;
  hostname: string;
  package_manager: string;
  pending_count: number;
  installed_count: number;
  updated_at: string | null;
  pending_updates: AgentInventoryDetailItem[];
  installed_updates: AgentInventoryDetailItem[];
};
