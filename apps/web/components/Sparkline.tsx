"use client";
// Sparkline SVG minimal para series temporales.
export default function Sparkline({ values, color = "#37D08A", h = 70 }: { values: number[]; color?: string; h?: number }) {
  if (values.length < 2) return <div className="spark" style={{ display: "grid", placeItems: "center", color: "#5c6f65", fontSize: 11 }}>sin datos</div>;
  const w = 420;
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - 8 - ((v - min) / span) * (h - 16);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const area = `0,${h} ${pts.join(" ")} ${w},${h}`;
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polygon points={area} fill={color} opacity="0.12" />
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}
