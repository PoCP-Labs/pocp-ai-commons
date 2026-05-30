/**
 * PoCP AI Commons — User Menu
 * ==============================
 * Compact user info display for the app header.
 * Shows user name, email, wallet balances, and logout button.
 */

import { useAuth } from "./AuthContext";

export default function UserMenu() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div style={styles.container}>
      <div style={styles.avatar}>
        {user.name.charAt(0).toUpperCase()}
      </div>
      <div style={styles.info}>
        <span style={styles.name}>{user.name}</span>
        <span style={styles.email}>{user.email}</span>
      </div>
      <div style={styles.badges}>
        <span style={styles.badge} title="AI Credits">
          {user.ai_credits.toFixed(1)} Credits
        </span>
        <span style={{ ...styles.badge, background: "#f0fdf4", color: "#059669" }} title="Contribution Points">
          {user.cp_balance.toFixed(1)} CP
        </span>
      </div>
      <button
        type="button"
        onClick={logout}
        style={styles.logoutBtn}
        title="Sign out"
      >
        Sign Out
      </button>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "8px 12px",
    background: "#f8fafc",
    borderRadius: 8,
    border: "1px solid #e2e8f0",
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "#2563eb",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 14,
    flexShrink: 0,
  },
  info: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  name: {
    fontSize: 14,
    fontWeight: 600,
    color: "#1e293b",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  email: {
    fontSize: 12,
    color: "#64748b",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  badges: {
    display: "flex",
    gap: 6,
    marginLeft: "auto",
  },
  badge: {
    padding: "3px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
    background: "#eff6ff",
    color: "#2563eb",
    whiteSpace: "nowrap",
  },
  logoutBtn: {
    padding: "6px 12px",
    borderRadius: 6,
    border: "1px solid #e2e8f0",
    background: "#fff",
    color: "#64748b",
    fontSize: 12,
    fontWeight: 500,
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
};
