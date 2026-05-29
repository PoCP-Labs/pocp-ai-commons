/**
 * PoCP AI Commons — Token Storage
 * =================================
 * Manages JWT access/refresh tokens in localStorage with a clean API.
 *
 * Security notes:
 * - Access tokens are short-lived (30 min) and stored in memory + localStorage.
 * - Refresh tokens are stored in localStorage for persistence across page reloads.
 * - In production, consider httpOnly cookies for refresh tokens.
 */

const ACCESS_TOKEN_KEY = "pocp_access_token";
const REFRESH_TOKEN_KEY = "pocp_refresh_token";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
  }
  if (refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
  }
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Decode the payload of a JWT token (without verification).
 * Used only for reading expiry/claims on the client side.
 */
export function decodeTokenPayload(token) {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

/**
 * Check if the access token is expired (with 60s buffer).
 */
export function isTokenExpired(token) {
  const payload = decodeTokenPayload(token);
  if (!payload || !payload.exp) return true;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < now + 60; // 60s buffer before actual expiry
}
