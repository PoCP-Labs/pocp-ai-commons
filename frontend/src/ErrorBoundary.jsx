import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("[PoCP UI]", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            maxWidth: 720,
            margin: "2rem auto",
            padding: "1.5rem",
            color: "#e8edf4",
            fontFamily: "system-ui, sans-serif",
            lineHeight: 1.5,
          }}
        >
          <h1 style={{ color: "#f87171", fontSize: "1.25rem" }}>PoCP UI failed to load</h1>
          <p style={{ color: "#8b95a5" }}>
            The dashboard hit a JavaScript error. Copy the message below if you need support.
          </p>
          <pre
            style={{
              marginTop: "1rem",
              padding: "1rem",
              background: "#111820",
              border: "1px solid rgba(248,113,113,0.35)",
              borderRadius: 8,
              overflow: "auto",
              whiteSpace: "pre-wrap",
              fontSize: "0.85rem",
            }}
          >
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <button
            type="button"
            style={{
              marginTop: "1rem",
              padding: "0.5rem 1rem",
              background: "#f7931a",
              border: "none",
              borderRadius: 8,
              cursor: "pointer",
              fontWeight: 600,
            }}
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
