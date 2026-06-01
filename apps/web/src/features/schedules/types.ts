export type ScheduleItem = {
  id: string;
  name: string;
  scope: string;
  scope_type: ScheduleScopeType;
  scope_value: string;
  cron_label: string;
  install_date: string | null;
  install_time: string;
  reboot_date: string | null;
  reboot_time: string | null;
  recurrence: ScheduleRecurrence;
  reboot_policy: string;
};

export type ScheduleScopeType = "machine" | "group" | "os";
export type ScheduleRecurrence = "once" | "daily" | "weekly" | "monthly";
export type ScheduleRebootPolicy = "if-needed" | "always" | "never";

export type ScheduleCreate = {
  name: string;
  scope_type: ScheduleScopeType;
  scope_value: string;
  install_date: string | null;
  install_time: string;
  reboot_date: string | null;
  reboot_time: string | null;
  recurrence: ScheduleRecurrence;
  reboot_policy: ScheduleRebootPolicy;
};
