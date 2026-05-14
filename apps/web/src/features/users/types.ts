export type UserRole = {
  value: "admin" | "user";
  label: string;
  description: string;
};

export type ManagedUser = {
  id: string;
  username: string;
  full_name: string;
  avatar_initials: string | null;
  avatar_color: string | null;
  role: "admin" | "user";
  is_active: boolean;
  must_change_password: boolean;
  password_changed_at: string | null;
  created_at: string;
};

export type UserCreatePayload = {
  username: string;
  full_name: string;
  password: string;
  role: "admin" | "user";
  avatar_initials: string | null;
  avatar_color: string | null;
  is_active: boolean;
  must_change_password: boolean;
};

export type UserUpdatePayload = {
  full_name: string;
  role: "admin" | "user";
  avatar_initials: string | null;
  avatar_color: string | null;
  is_active: boolean;
  must_change_password: boolean;
};

export type UserPasswordResetPayload = {
  new_password: string;
  must_change_password: boolean;
};
