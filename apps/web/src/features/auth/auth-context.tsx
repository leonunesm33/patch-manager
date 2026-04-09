import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fetchCurrentUser, loginRequest } from "@/features/auth/api";
import type { User } from "@/features/auth/types";

const AUTH_TOKEN_KEY = "patch-manager-token";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function getStoredToken() {
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

function setStoredToken(token: string | null) {
  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      if (!token) {
        if (active) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const currentUser = await fetchCurrentUser(token);
        if (!active) return;
        setUser(currentUser);
      } catch {
        if (!active) return;
        setStoredToken(null);
        setToken(null);
        setUser(null);
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void bootstrap();

    return () => {
      active = false;
    };
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isLoading,
      async login(username: string, password: string) {
        const response = await loginRequest({ username, password });
        setStoredToken(response.access_token);
        setToken(response.access_token);
        const currentUser = await fetchCurrentUser(response.access_token);
        setUser(currentUser);
        setIsLoading(false);
      },
      logout() {
        setStoredToken(null);
        setToken(null);
        setUser(null);
      },
    }),
    [token, user, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
