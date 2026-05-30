/**
 * PoCP AI Commons — Auth Context
 * =================================
 * React Context providing authentication state and actions to the entire app.
 *
 * Provides:
 * - user: current user profile (or null if not logged in)
 * - isAuthenticated: boolean
 * - isLoading: boolean (initial auth check in progress)
 * - login(email, password): Promise
 * - register(email, password, name, description): Promise
 * - logout(): Promise
 * - refreshProfile(): Promise
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authGet, authPost, API_BASE } from "./apiClient";
import { clearTokens, getAccessToken, setTokens } from "./tokenStorage";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user is already logged in on mount
  const refreshProfile = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const profile = await authGet("/api/v1/auth/me");
      setUser(profile);
    } catch {
      setUser(null);
      clearTokens();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

  // Login action
  const login = useCallback(async (email, password) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Login failed");
    }

    const tokens = await res.json();
    setTokens(tokens);

    // Fetch profile
    const profile = await authGet("/api/v1/auth/me");
    setUser(profile);
    return profile;
  }, []);

  // Register action
  const register = useCallback(async (email, password, name, description) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name, description }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Registration failed");
    }

    const data = await res.json();
    setTokens(data);

    // Fetch profile
    const profile = await authGet("/api/v1/auth/me");
    setUser(profile);
    return profile;
  }, []);

  // Logout action
  const logout = useCallback(async () => {
    try {
      await authPost("/api/v1/auth/logout", {});
    } catch {
      // Ignore errors during logout
    } finally {
      clearTokens();
      setUser(null);
    }
  }, []);

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access auth context.
 * Must be used within an AuthProvider.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
