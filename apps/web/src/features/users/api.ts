import { http } from "@/lib/http";
import type {
  ManagedUser,
  UserCreatePayload,
  UserPasswordResetPayload,
  UserRole,
  UserUpdatePayload,
} from "@/features/users/types";

export function fetchUserRoles() {
  return http<UserRole[]>("/users/roles");
}

export function fetchUsers() {
  return http<ManagedUser[]>("/users");
}

export function createUser(payload: UserCreatePayload) {
  return http<ManagedUser>("/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateUser(userId: string, payload: UserUpdatePayload) {
  return http<ManagedUser>(`/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function resetUserPassword(userId: string, payload: UserPasswordResetPayload) {
  return http<ManagedUser>(`/users/${encodeURIComponent(userId)}/reset-password`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
