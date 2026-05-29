/**
 * PoCP AI Commons — Auth Gate (Route Guard)
 * ============================================
 * Wraps the main application content.
 * Shows login/register pages when unauthenticated.
 * Shows the app content when authenticated.
 *
 * This is a lightweight alternative to react-router for this simple app.
 */

import { useState } from "react";
import { useAuth } from "./AuthContext";
import LoginPage from "./LoginPage";
import RegisterPage from "./RegisterPage";

export default function AuthGate({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const [authView, setAuthView] = useState("login"); // "login" | "register"

  // Show loading spinner during initial auth check
  if (isLoading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.spinner} />
        <p style={styles.loadingText}>Loading PoCP AI Commons...</p>
      </div>
    );
  }

  // Show auth pages when not authenticated
  if (!isAuthenticated) {
    if (authView === "register") {
      return <RegisterPage onSwitchToLogin={() => setAuthView("login")} />;
    }
    return <LoginPage onSwitchToRegister={() => setAuthView("register")} />;
  }

  // Authenticated — render the app
  return children;
}

const styles = {
  loadingContainer: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "system-ui, sans-serif",
    background: "#f8fafc",
  },
  spinner: {
    width: 32,
    height: 32,
    border: "3px solid #e2e8f0",
    borderTopColor: "#2563eb",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  loadingText: {
    marginTop: 16,
    color: "#64748b",
    fontSize: 14,
  },
};
