export type Machine = {
  id: string;
  name: string;
  ip: string;
  platform: string;
  group: string;
  status: "online" | "warning" | "offline";
  pending_patches: number;
  last_check_in: string;
  risk: "critical" | "important" | "optional";
};
