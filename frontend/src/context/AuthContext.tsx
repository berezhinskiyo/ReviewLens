import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  api,
  clearRefreshToken,
  getRefreshToken,
  publicApi,
  setRefreshToken,
} from "../api/client";
import type { TokenResponse, UserMe } from "../types";

type AuthContextValue = {
  token: string | null;
  user: UserMe | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  requestRegisterCode: (
    email: string,
    password: string,
    captchaToken?: string
  ) => Promise<void>;
  verifyRegisterCode: (email: string, code: string) => Promise<void>;
  completeOAuthLogin: (accessToken: string, refreshToken: string) => Promise<void>;
  refreshMe: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async (access: string) => {
    const me = await api<UserMe>("/auth/me", {}, access);
    setUser(me);
    setToken(access);
  }, []);

  const refreshMe = useCallback(async () => {
    if (token) await loadMe(token);
  }, [token, loadMe]);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const rt = getRefreshToken();
        if (!rt) {
          setLoading(false);
          return;
        }
        const data = await api<TokenResponse>("/auth/refresh", {
          method: "POST",
          body: JSON.stringify({ refresh_token: rt }),
        });
        setRefreshToken(data.refresh_token);
        await loadMe(data.access_token);
      } catch {
        clearRefreshToken();
      } finally {
        setLoading(false);
      }
    };
    void bootstrap();
  }, [loadMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await publicApi<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setRefreshToken(data.refresh_token);
      await loadMe(data.access_token);
    },
    [loadMe]
  );

  const requestRegisterCode = useCallback(
    async (email: string, password: string, captchaToken?: string) => {
      await publicApi("/auth/register/request-code", {
        method: "POST",
        body: JSON.stringify({ email, password, captcha_token: captchaToken }),
      });
    },
    []
  );

  const verifyRegisterCode = useCallback(
    async (email: string, code: string) => {
      const data = await publicApi<TokenResponse>("/auth/register/verify", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      });
      setRefreshToken(data.refresh_token);
      await loadMe(data.access_token);
    },
    [loadMe]
  );

  const completeOAuthLogin = useCallback(
    async (accessToken: string, refreshToken: string) => {
      setRefreshToken(refreshToken);
      await loadMe(accessToken);
    },
    [loadMe]
  );

  const logout = useCallback(async () => {
    const rt = getRefreshToken();
    if (rt) {
      try {
        await api(
          "/auth/logout",
          { method: "POST", body: JSON.stringify({ refresh_token: rt }) },
          token
        );
      } catch {
        /* ignore */
      }
    }
    clearRefreshToken();
    setToken(null);
    setUser(null);
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      login,
      requestRegisterCode,
      verifyRegisterCode,
      completeOAuthLogin,
      refreshMe,
      logout,
    }),
    [
      token,
      user,
      loading,
      login,
      requestRegisterCode,
      verifyRegisterCode,
      completeOAuthLogin,
      refreshMe,
      logout,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
