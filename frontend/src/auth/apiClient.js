/**
 * PoCP AI Commons — Authenticated API Client
 * =============================================
 * A fetch wrapper that:
 * 1. Automatically attaches the Bearer access token to requests.
 * 2. Transparently refreshes expired tokens before retrying.
 * 3. Redirects to login on unrecoverable auth failures.
 *
 * Usage:
 *   import { authFetch, authPost } from "./auth/apiClient";
 *   const data = await authFetch("/api/v1/auth/me");
 *   const result = await authPost("/api/v1/protected/tasks", { title: "..." });
 */

import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  isTokenExpired,
} from "./tokenStorage";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Mutex to prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshPromise = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns true on success, false on failure.
 */
async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      clearTokens();
      return false;
    }

    const data = await res.json();
    setTokens(data);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

/**
 * Ensure we have a valid access token, refreshing if necessary.
 * Uses a mutex to avoid concurrent refresh requests.
 */
async function ensureValidToken() {
  const token = getAccessToken();

  if (token && !isTokenExpired(token)) {
    return token;
  }

  // Need to refresh
  if (!isRefreshing) {
    isRefreshing = true;
    refreshPromise = refreshAccessToken().finally(() => {
      isRefreshing = false;
      refreshPromise = null;
    });
  }

  const success = await refreshPromise;
  if (!success) {
    return null;
  }

  return getAccessToken();
}

/**
 * Authenticated fetch wrapper.
 * Automatically attaches Authorization header and handles token refresh.
 */
export async function authFetch(path, options = {}) {
  const token = await ensureValidToken();

  const headers = {
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  let res = await fetch(url, { ...options, headers });

  // If 401, try one more refresh cycle
  if (res.status === 401 && token) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      const newToken = getAccessToken();
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(url, { ...options, headers });
    }
  }

  return res;
}

/**
 * Authenticated JSON GET request.
 */
export async function authGet(path) {
  const res = await authFetch(path);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Authenticated JSON POST request.
 */
export async function authPost(path, body) {
  const res = await authFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  // Handle 204 No Content (e.g., logout)
  if (res.status === 204) return null;
  return res.json();
}

/**
 * Public (unauthenticated) JSON GET — for endpoints that don't require auth.
 */
export async function publicGet(path) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/**
 * Public (unauthenticated) JSON POST.
 */
export async function publicPost(path, body) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export { API_BASE };
