export type ToggleSetting = {
  label: string;
  description: string;
  enabled: boolean;
};

export type SettingsResponse = {
  policy: ToggleSetting[];
  notifications: ToggleSetting[];
};
