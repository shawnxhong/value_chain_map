import { useEffect, useState } from "react";

import { apiGet, apiPost } from "../api/client";
import type { EdgeEvidence, EvidenceItem, GraphEdge } from "../types";

const STALENESS_WARN_MONTHS = 12; // mirrors backend VCM_STALENESS_WARN_MONTHS default

function monthsAgo(isoDate: string): number {
  const then = new Date(isoDate);
  const now = new Date();
  return (now.getFullYear() - then.getFullYear()) * 12 + (now.getMonth() - then.getMonth());
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 8, margin: "4px 0" }}>
      <span style={{ minWidth: 96, color: "#666", fontSize: 12 }}>{label}</span>
      <span style={{ fontSize: 13 }}>{children}</span>
    </div>
  );
}

interface Props {
  edge: GraphEdge;
  nodeName: (id: string) => string;
  onReviewed: () => void;
}

export default function EdgeDetailPanel({ edge, nodeName, onReviewed }: Props) {
  const [evidence, setEvidence] = useState<EvidenceItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    setEvidence(null);
    setError(null);
    setReviewError(null);
    apiGet<EdgeEvidence>(`/evidence/${edge.id}`)
      .then((r) => setEvidence(r.evidence))
      .catch((e: Error) => setError(e.message));
  }, [edge.id]);

  const review = (action: "confirm" | "reject") => {
    setReviewing(true);
    setReviewError(null);
    apiPost(`/review/edge/${edge.id}/${action}`, { actor: "reviewer" })
      .then(() => onReviewed())
      .catch((e: Error) => setReviewError(e.message))
      .finally(() => setReviewing(false));
  };

  const stale = monthsAgo(edge.as_of_date) >= STALENESS_WARN_MONTHS;

  return (
    <aside
      style={{
        width: 360,
        padding: "12px 16px",
        border: "1px solid #ddd",
        borderRadius: 8,
        overflowY: "auto",
        maxHeight: 560,
      }}
    >
      <h3 style={{ margin: "0 0 8px" }}>
        {nodeName(edge.source)} → {nodeName(edge.target)}
      </h3>
      <Row label="Relationship">{edge.relationship_type}</Row>
      <Row label="Layer">
        {edge.layer}
        {edge.layer !== "fact" && (
          <span style={{ color: "#b26a00" }}> (unverified — weaker)</span>
        )}
      </Row>
      <Row label="Confidence">
        {edge.confidence_label} — <span style={{ color: "#666" }}>{edge.confidence_reason}</span>
      </Row>
      {edge.payer_node_id && edge.receiver_node_id && (
        <Row label="Pays">
          {nodeName(edge.payer_node_id)} → {nodeName(edge.receiver_node_id)}
          {edge.payment_type ? ` (${edge.payment_type})` : ""}
        </Row>
      )}
      {edge.concentration_pct && <Row label="Concentration">{edge.concentration_pct}</Row>}
      <Row label="Status">{edge.status}</Row>
      <Row label="As of">
        <span style={{ color: stale ? "#c0392b" : "inherit" }}>
          {edge.as_of_date} ({monthsAgo(edge.as_of_date)} months ago{stale ? " — stale" : ""})
        </span>
      </Row>

      {(edge.status === "candidate" || edge.status === "confirmed") && (
        <div style={{ display: "flex", gap: 8, margin: "10px 0 2px" }}>
          {edge.status === "candidate" && (
            <button type="button" disabled={reviewing} onClick={() => review("confirm")}>
              Confirm
            </button>
          )}
          <button type="button" disabled={reviewing} onClick={() => review("reject")}>
            Reject
          </button>
        </div>
      )}
      {reviewError && <p style={{ color: "crimson", fontSize: 12 }}>Review failed: {reviewError}</p>}

      <h4 style={{ margin: "14px 0 6px" }}>Evidence</h4>
      {error && <p style={{ color: "crimson", fontSize: 12 }}>Could not load evidence: {error}</p>}
      {!error && evidence === null && <p style={{ fontSize: 12 }}>Loading…</p>}
      {evidence !== null && evidence.length === 0 && (
        <p style={{ fontSize: 12, color: "#666" }}>No bound excerpts.</p>
      )}
      {evidence?.map((ev) => (
        <blockquote
          key={ev.id}
          style={{
            margin: "0 0 10px",
            padding: "8px 10px",
            background: "#f7f5ef",
            borderLeft: "3px solid #c9c2ad",
            borderRadius: 4,
            fontSize: 13,
          }}
        >
          <div>“{ev.excerpt}”</div>
          <div style={{ marginTop: 6, fontSize: 11, color: "#666" }}>
            {ev.source_type} — {ev.title}
            {ev.url && (
              <>
                {" · "}
                <a href={ev.url} target="_blank" rel="noreferrer">
                  source
                </a>
              </>
            )}
          </div>
        </blockquote>
      ))}
    </aside>
  );
}
