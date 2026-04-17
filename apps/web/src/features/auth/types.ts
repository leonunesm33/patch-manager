export type LoginRequest = {
  username: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  must_change_password: boolean;
  role: string;
};

export type User = {
  id: string;
  username: string;
  full_name: string;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  password_changed_at: string | null;
};

export type PasswordChangeRequest = {
  current_password: string;
  new_password: string;
};
