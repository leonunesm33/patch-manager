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
  post_patch_state: string | null;
  post_patch_message: string | null;
  last_apply_at: string | null;
  reboot_scheduled_at: string | null;
};

export type MachineCreate = {
  name: string;
  ip: string;
  platform: string;
  group: string;
  status: "online" | "warning" | "offline";
  pending_patches: number;
  risk: "critical" | "important" | "optional";
};
