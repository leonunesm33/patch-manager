export type LoginRequest = {
  username: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type User = {
  id: string;
  username: string;
  full_name: string;
  is_active: boolean;
};
