/**
 * PoCP AI Commons — Register Page
 * ==================================
 * Registration form for new contributors.
 * Creates a human Entity + Account and grants starter AI Credits.
 */

import { useState } from "react";
import { useAuth } from "./AuthContext";

export default function RegisterPage({ onSwitchToLogin }) {
  const { register } = useAuth();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    description: "",
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      await register(form.email, form.password, form.name, form.description || null);
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
          <h1 style={styles.title}>Join PoCP AI Commons</h1>
          <p style={styles.subtitle}>
            Create your contributor account and receive 100 AI Credits
          </p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>
            Display Name
            <input
              type="text"
              value={form.name}
              onChange={(e) => updateField("name", e.target.value)}
              placeholder="Your display name"
              required
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(e) => updateField("email", e.target.value)}
              placeholder="you@example.com"
              required
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(e) => updateField("password", e.target.value)}
              placeholder="Minimum 8 characters"
              required
              minLength={8}
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Confirm Password
            <input
              type="password"
              value={form.confirmPassword}
              onChange={(e) => updateField("confirmPassword", e.target.value)}
              placeholder="Re-enter your password"
              required
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            Bio (optional)
            <textarea
              value={form.description}
              onChange={(e) => updateField("description", e.target.value)}
              placeholder="Tell us about your contribution interests..."
              rows={3}
              style={{ ...styles.input, resize: "vertical" }}
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
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <div style={styles.footer}>
          <p style={styles.footerText}>
            Already have an account?{" "}
            <button
              type="button"
              onClick={onSwitchToLogin}
              style={styles.linkButton}
            >
              Sign in
            </button>
          </p>
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
    marginBottom: "1.5rem",
  },
  title: {
    margin: 0,
    fontSize: 22,
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
    gap: 14,
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
    background: "#059669",
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
};
