export type ScheduleItem = {
  id: string;
  name: string;
  scope: string;
  cron_label: string;
  reboot_policy: string;
};

export type ScheduleCreate = {
  name: string;
  scope: string;
  cron_label: string;
  reboot_policy: string;
};
