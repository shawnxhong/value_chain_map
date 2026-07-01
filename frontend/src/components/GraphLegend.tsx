// Overlay legend + canvas controls for the value-chain graph. Presentational; the color key
// mirrors graph/style.ts (NODE_COLORS) and the edge key mirrors the design §7.5 styling.

import { NODE_COLORS } from "../graph/style";

const NODE_LEGEND: { label: string; type: keyof typeof NODE_COLORS }[] = [
  { label: "Company", type: "company" },
  { label: "Stage", type: "value_chain_stage" },
  { label: "Product", type: "product" },
  { label: "End market", type: "end_market" },
  { label: "Technology", type: "technology" },
];

function Chip({ color }: { color: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 12,
        height: 12,
        borderRadius: 3,
        background: color,
        border: "1px solid rgba(0,0,0,0.18)",
      }}
    />
  );
}

function Line({ color, dash }: { color: string; dash?: boolean }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 18,
        borderTop: `2px ${dash ? "dashed" : "solid"} ${color}`,
        marginBottom: 3,
      }}
    />
  );
}

interface Props {
  onFit: () => void;
  onRelayout: () => void;
}

export default function GraphLegend({ onFit, onRelayout }: Props) {
  return (
    <div
      style={{
        position: "absolute",
        top: 8,
        right: 8,
        zIndex: 10,
        background: "rgba(255,255,255,0.92)",
        border: "1px solid #e3e3e3",
        borderRadius: 8,
        padding: "8px 10px",
        fontSize: 11,
        color: "#333",
        maxWidth: 190,
        boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
      }}
    >
      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        <button type="button" onClick={onFit} style={{ fontSize: 11, padding: "2px 8px" }}>
          Fit
        </button>
        <button type="button" onClick={onRelayout} style={{ fontSize: 11, padding: "2px 8px" }}>
          Re-layout
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "3px 6px", alignItems: "center" }}>
        {NODE_LEGEND.map((n) => (
          <FragmentRow key={n.type} left={<Chip color={NODE_COLORS[n.type]} />} label={n.label} />
        ))}
      </div>

      <hr style={{ border: 0, borderTop: "1px solid #eee", margin: "8px 0" }} />

      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "3px 6px", alignItems: "center" }}>
        <FragmentRow left={<Line color="#1a7f37" />} label="Fact" />
        <FragmentRow left={<Line color="#9aa0a6" dash />} label="Inference / thesis" />
        <FragmentRow left={<Line color="#c2557a" dash />} label="Competes" />
        <FragmentRow left={<Line color="#16a085" dash />} label="Migrates to" />
      </div>
    </div>
  );
}

// small helper so each legend row is two grid cells (chip/line, then label)
function FragmentRow({ left, label }: { left: React.ReactNode; label: string }) {
  return (
    <>
      <span style={{ display: "flex", alignItems: "center" }}>{left}</span>
      <span>{label}</span>
    </>
  );
}
