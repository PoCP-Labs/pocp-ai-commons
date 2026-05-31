import { useState } from "react";

const EVENT_TYPES = [
  { value: "contact_sent", label: "Contact sent" },
  { value: "response_received", label: "Response received" },
  { value: "meeting_scheduled", label: "Meeting scheduled" },
  { value: "proposal_shared", label: "Proposal shared" },
  { value: "status_advanced", label: "Status advanced" },
  { value: "note", label: "Note" },
];

const STATUS_OPTIONS = [
  { value: "", label: "Keep current status" },
  { value: "outreach", label: "Outreach" },
  { value: "in_conversation", label: "In conversation" },
  { value: "active_partner", label: "Active partner" },
  { value: "federation_peer", label: "Federation peer" },
  { value: "integrated", label: "Integrated" },
  { value: "paused", label: "Paused" },
];

export default function LogOutreachForm({
  slug,
  currentStatus,
  fetchJson,
  authenticated,
  onSuccess,
  compact = false,
}) {
  const [open, setOpen] = useState(false);
  const [eventType, setEventType] = useState("contact_sent");
  const [notes, setNotes] = useState("");
  const [newStatus, setNewStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!slug) return null;

  if (!authenticated) {
    return (
      <p className="outreach-hint" style={{ fontSize: "0.72rem", marginTop: compact ? 0 : 6 }}>
        Dev Login to log outreach.
      </p>
    );
  }

  const resetForm = () => {
    setEventType("contact_sent");
    setNotes("");
    setNewStatus("");
    setError(null);
    setSuccess(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await fetchJson(`/api/v1/community-partners/partners/${slug}/outreach`, {
        method: "POST",
        body: JSON.stringify({
          event_type: eventType,
          notes: notes.trim(),
          new_status: newStatus || null,
        }),
      });
      const entry = result.entry || {};
      setEventType("contact_sent");
      setNotes("");
      setNewStatus("");
      setError(null);
      setOpen(false);
      if (onSuccess) await onSuccess(result);
      void entry;
    } catch (err) {
      setError(err.message || "Could not log outreach");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        className={`btn btn--sm${compact ? " btn--primary" : " btn--ghost"}`}
        onClick={() => {
          resetForm();
          setOpen(true);
        }}
      >
        Log outreach
      </button>
    );
  }

  return (
    <form className="outreach-form" onSubmit={handleSubmit}>
      <label className="outreach-form__label">
        Event
        <select
          className="outreach-form__input"
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
          disabled={loading}
        >
          {EVENT_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
      <label className="outreach-form__label">
        Notes
        <textarea
          className="outreach-form__input outreach-form__textarea"
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What happened? Link to thread or draft."
          disabled={loading}
        />
      </label>
      <label className="outreach-form__label">
        New status
        <select
          className="outreach-form__input"
          value={newStatus}
          onChange={(e) => setNewStatus(e.target.value)}
          disabled={loading}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value || "keep"} value={opt.value}>
              {opt.value ? opt.label : `${opt.label}${currentStatus ? ` (${currentStatus})` : ""}`}
            </option>
          ))}
        </select>
      </label>
      {error && <p className="outreach-form__error">{error}</p>}
      {success && <p className="outreach-form__success">{success} recorded.</p>}
      <div className="outreach-form__actions">
        <button type="submit" className="btn btn--sm btn--primary" disabled={loading}>
          {loading ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          disabled={loading}
          onClick={() => {
            resetForm();
            setOpen(false);
          }}
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
