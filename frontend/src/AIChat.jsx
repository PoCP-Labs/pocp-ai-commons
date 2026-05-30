import { useCallback, useEffect, useRef, useState } from "react";
import { publicPost, publicGet } from "./auth";

export default function AIChat({ user, entityId, onCreditsChange }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [history, setHistory] = useState([]);
  const [credits, setCredits] = useState(null);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  // Load chat history and wallet
  const load = useCallback(() => {
    if (!entityId) return;
    setError(null);
    Promise.all([
      publicGet(`/api/v1/chat/history?entity_id=${entityId}&limit=5`),
      publicGet("/api/v1/wallets"),
    ])
      .then(([hist, wallets]) => {
        setHistory(hist);
        const wallet = wallets.find((w) => w.entity_id === entityId);
        if (wallet) setCredits(wallet.ai_credits);
      })
      .catch((err) => {
        // Chat history may not exist yet — that's ok
        if (!err?.includes("404")) setError(err);
      });
  }, [entityId]);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    setSending(true);
    setError(null);

    const userMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const result = await publicPost("/api/v1/chat", {
        entity_id: entityId,
        message: text,
        model_provider: "deepseek",
      });

      const aiMessage = {
        id: `msg-${Date.now()}-ai`,
        role: "assistant",
        content: result.reply,
        creditsUsed: result.credits_used,
      };
      setMessages((prev) => [...prev, aiMessage]);
      setCredits(result.credits_remaining);
      if (onCreditsChange) onCreditsChange(result.credits_remaining);
    } catch (err) {
      const errorMsg = err?.includes("402")
        ? "⚠️ Not enough AI Credits! Earn more by contributing."
        : `❌ ${err || "Failed to send message"}`;
      setMessages((prev) => [
        ...prev,
        { id: `msg-err-${Date.now()}`, role: "system", content: errorMsg },
      ]);
    }

    setSending(false);
  }, [input, sending, entityId, onCreditsChange]);

  const handleKeyDown = (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      sendMessage();
    }
  };

  const creditColor = credits !== null
    ? credits > 50 ? "#059669" : credits > 10 ? "#d97706" : "#dc2626"
    : "#94a3b8";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        border: "1px solid #e2e8f0",
        borderRadius: 12,
        overflow: "hidden",
        background: "#fff",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "#f8fafc",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: creditColor,
              display: "inline-block",
            }}
          />
          <strong>AI Chat</strong>
        </div>
        <div style={{ fontSize: 13, color: "#475569" }}>
          <span style={{ color: creditColor, fontWeight: 600 }}>
            {credits !== null ? `${credits.toFixed(1)}` : "..."}
          </span>{" "}
          AI Credits
        </div>
      </div>

      {/* Messages Area */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          background: "#fafbfc",
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              color: "#94a3b8",
              padding: "3rem 1rem",
              fontSize: 14,
            }}
          >
            <div style={{ fontSize: 32, marginBottom: 8 }}>🤖</div>
            <p style={{ margin: 0 }}>AI Chat is ready</p>
            <p style={{ margin: "4px 0 0", fontSize: 13 }}>
              Each message consumes AI Credits from your wallet.
              <br />
              Earn more by completing contribution tasks.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {sending && (
          <div
            style={{
              alignSelf: "flex-start",
              background: "#e2e8f0",
              padding: "8px 16px",
              borderRadius: "4px 16px 16px 16px",
              fontSize: 14,
              color: "#64748b",
            }}
          >
            <span style={{ display: "inline-flex", gap: 3 }}>
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid #e2e8f0",
          display: "flex",
          gap: 8,
          background: "#fff",
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Enter to send)"
          disabled={sending}
          style={{
            flex: 1,
            padding: "10px 14px",
            border: "1px solid #d1d5db",
            borderRadius: 8,
            fontSize: 14,
            outline: "none",
            fontFamily: "inherit",
          }}
          autoFocus
        />
        <button
          onClick={sendMessage}
          disabled={sending || !input.trim()}
          style={{
            padding: "10px 20px",
            background: !input.trim() ? "#e2e8f0" : "#2563eb",
            color: !input.trim() ? "#94a3b8" : "#fff",
            border: "none",
            borderRadius: 8,
            cursor: !input.trim() ? "default" : "pointer",
            fontSize: 14,
            fontWeight: 600,
            transition: "background 0.15s",
          }}
        >
          {sending ? "..." : "Send"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: "8px 16px",
            background: "#fef2f2",
            color: "#dc2626",
            fontSize: 12,
            borderTop: "1px solid #fecaca",
          }}
        >
          {error}
        </div>
      )}

      {/* Inline styles for typing indicator */}
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
        .typing-dot {
          display: inline-block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #64748b;
          animation: blink 1.4s infinite;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
      `}</style>
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const isAssistant = message.role === "assistant";

  let bg, color, align, borderRadius;
  if (isUser) {
    bg = "#2563eb";
    color = "#fff";
    align = "flex-end";
    borderRadius = "16px 4px 16px 16px";
  } else if (isSystem) {
    bg = "#fef2f2";
    color = "#991b1b";
    align = "center";
    borderRadius = 8;
  } else {
    bg = "#f1f5f9";
    color = "#1e293b";
    align = "flex-start";
    borderRadius = "4px 16px 16px 16px";
  }

  return (
    <div style={{ alignSelf: align, maxWidth: "85%" }}>
      {isAssistant && (
        <div
          style={{
            fontSize: 11,
            color: "#64748b",
            marginBottom: 2,
            marginLeft: 4,
          }}
        >
          Assistant
        </div>
      )}
      <div
        style={{
          background: bg,
          color,
          padding: "10px 14px",
          borderRadius,
          fontSize: 14,
          lineHeight: 1.5,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {message.content}
        {message.creditsUsed !== undefined && (
          <div
            style={{
              fontSize: 11,
              marginTop: 6,
              opacity: 0.7,
              color: isUser ? "#93c5fd" : "#64748b",
            }}
          >
            −{message.creditsUsed} AI Credits
          </div>
        )}
      </div>
    </div>
  );
}
