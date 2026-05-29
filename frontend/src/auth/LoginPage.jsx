/**
 * PoCP AI Commons — Login Page
 * ===============================
 * Clean login form with email/password fields.
 * Matches the existing inline-style design language of the project.
 */

import { useState } from "react";
import { useAuth } from "./AuthContext";

export default function LoginPage({ onSwitchToRegister }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <h1 style={styles.title}>PoCP AI Commons</h1>
          <p style={styles.subtitle}>Sign in to your contribution account</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alice@pocp.dev"
              required
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              minLength={8}
              style={styles.input}
            />
          </label>

          {error && <p style={styles.error}>{error}</p>}

          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.button,
              opacity: loading ? 0.7 : 1,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div style={styles.footer}>
          <p style={styles.footerText}>
            Don't have an account?{" "}
            <button
              type="button"
              onClick={onSwitchToRegister}
              style={styles.linkButton}
            >
              Create one
            </button>
          </p>
          <div style={styles.demoBox}>
            <p style={styles.demoTitle}>Demo Accounts</p>
            <p style={styles.demoText}>
              <strong>Alice</strong> (contributor): alice@pocp.dev / alice12345
            </p>
            <p style={styles.demoText}>
              <strong>Bob</strong> (admin): bob@pocp.dev / bob12345
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0fdf4 100%)",
    fontFamily: "system-ui, sans-serif",
    padding: "1rem",
  },
  card: {
    background: "#fff",
    borderRadius: 12,
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    padding: "2.5rem",
    width: "100%",
    maxWidth: 420,
  },
  header: {
    textAlign: "center",
    marginBottom: "2rem",
  },
  title: {
    margin: 0,
    fontSize: 24,
    color: "#1e293b",
  },
  subtitle: {
    margin: "8px 0 0",
    color: "#64748b",
    fontSize: 14,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    fontSize: 14,
    fontWeight: 500,
    color: "#334155",
  },
  input: {
    padding: "10px 12px",
    borderRadius: 8,
    border: "1px solid #cbd5e1",
    fontSize: 14,
    outline: "none",
    transition: "border-color 0.2s",
  },
  button: {
    marginTop: 8,
    padding: "12px 16px",
    borderRadius: 8,
    border: "none",
    background: "#2563eb",
    color: "#fff",
    fontSize: 15,
    fontWeight: 600,
  },
  error: {
    margin: 0,
    padding: "8px 12px",
    borderRadius: 6,
    background: "#fef2f2",
    color: "#dc2626",
    fontSize: 13,
  },
  footer: {
    marginTop: "1.5rem",
    textAlign: "center",
  },
  footerText: {
    color: "#64748b",
    fontSize: 14,
  },
  linkButton: {
    background: "none",
    border: "none",
    color: "#2563eb",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
    padding: 0,
  },
  demoBox: {
    marginTop: 16,
    padding: 12,
    background: "#f8fafc",
    borderRadius: 8,
    border: "1px solid #e2e8f0",
    textAlign: "left",
  },
  demoTitle: {
    margin: "0 0 6px",
    fontSize: 12,
    fontWeight: 600,
    color: "#475569",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  demoText: {
    margin: "2px 0",
    fontSize: 12,
    color: "#64748b",
  },
};
