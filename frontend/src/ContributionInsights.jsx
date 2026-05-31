import { useEffect, useState } from "react";

export default function ContributionInsights({ contributionId, fetchJson, onSelectEntity }) {
  const [inspirations, setInspirations] = useState(null);
  const [partners, setPartners] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!contributionId || !fetchJson) {
      setInspirations(null);
      setPartners(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all([
      fetchJson(`/api/v1/contributions/${contributionId}/external-inspirations`).catch(
        () => ({ inspirations: [] })
      ),
      fetchJson(`/api/v1/contributions/${contributionId}/community-partners`).catch(
        () => ({ matched_partners: [] })
      ),
    ])
      .then(([insp, part]) => {
        if (cancelled) return;
        setInspirations(insp);
        setPartners(part);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [contributionId, fetchJson]);

  if (!contributionId) return null;

  const inspList = inspirations?.inspirations || [];
  const partnerList = partners?.matched_partners || [];
  const hasInsp = inspList.length > 0;
  const hasPartners = partnerList.length > 0;

  if (loading && !hasInsp && !hasPartners) {
    return (
      <div className="proof-layers" style={{ marginTop: 12 }}>
        <p className="proof-layers__meta">Loading ecosystem context…</p>
      </div>
    );
  }

  if (!hasInsp && !hasPartners) return null;

  return (
    <div className="proof-layers" style={{ marginTop: 12 }}>
      <h4 className="proof-layers__title">Ecosystem context</h4>

      {hasInsp && (
        <div className="proof-layers__card">
          <strong>External inspiration patterns</strong>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: "0.8rem" }}>
            {inspList.map((item) => (
              <li key={item.slug || item.entity_id}>
                {item.display_name || item.slug}
                {item.matched_modules?.length > 0 && (
                  <span className="proof-layers__meta"> · {item.matched_modules[0]}</span>
                )}
                {item.entity_id && onSelectEntity && (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      style={{ marginLeft: 4, padding: "2px 6px" }}
                      onClick={() => onSelectEntity(item.entity_id)}
                    >
                      entity
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasPartners && (
        <div className="proof-layers__card" style={{ marginTop: 8 }}>
          <strong>Aligned community partners</strong>
          <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: "0.8rem" }}>
            {partnerList.map((p) => (
              <li key={p.slug}>
                {p.display_name || p.slug}
                {p.capability && <span className="proof-layers__meta"> · {p.capability}</span>}
                {p.entity_id && onSelectEntity && (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      style={{ marginLeft: 4, padding: "2px 6px" }}
                      onClick={() => onSelectEntity(p.entity_id)}
                    >
                      entity
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
