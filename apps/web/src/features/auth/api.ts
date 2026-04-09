import { http } from "@/lib/http";
import type { LoginRequest, TokenResponse, User } from "@/features/auth/types";

export function loginRequest(payload: LoginRequest) {
  return http<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchCurrentUser(token: string) {
  return http<User>("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
