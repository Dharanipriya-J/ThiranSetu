import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { api, getToken, setToken, setUnauthorizedHandler } from '../api/client';
import type { LoginRequest, RegisterRequest, User } from '../api/types';

interface AuthCtx {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (body: LoginRequest) => Promise<void>;
  register: (body: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx | null>(null);

function hasSessionCookie(): boolean {
  try {
    return typeof document !== 'undefined' && document.cookie.includes('ts_csrf=');
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() => !getToken() && hasSessionCookie());
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const clearSession = useCallback(() => {
    setToken(null);
    setTokenState(null);
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearSession();
      navigate('/login', { replace: true, state: { expired: true } });
    });
  }, [clearSession, navigate]);

  useEffect(() => {
    if (getToken() || !hasSessionCookie()) return;
    let active = true;
    api
      .refresh()
      .then((res) => {
        if (!active) return;
        setToken(res.access_token);
        setTokenState(res.access_token);
        setUser(res.user);
      })
      .catch(() => {
        if (active) clearSession();
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [clearSession]);

  const applySession = useCallback((accessToken: string, u: User) => {
    setToken(accessToken);
    setTokenState(accessToken);
    setUser(u);
  }, []);

  const login = useCallback(
    async (body: LoginRequest) => {
      const res = await api.login(body);
      applySession(res.access_token, res.user);
    },
    [applySession],
  );

  const register = useCallback(
    async (body: RegisterRequest) => {
      const res = await api.register(body);
      applySession(res.access_token, res.user);
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* server-side revocation is best effort; local session is cleared regardless */
    }
    clearSession();
    navigate('/login', { replace: true });
  }, [clearSession, navigate]);

  const value = useMemo(
    () => ({ token, user, isAuthenticated: Boolean(token), isLoading, login, register, logout }),
    [token, user, isLoading, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
