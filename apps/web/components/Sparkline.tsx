"use client";
// Sparkline SVG minimal para series temporales.
export default function Sparkline({ values, color = "#37D08A", h = 70 }: { values: number[]; color?: string; h?: number }) {
  const puntos = values.filter((valor) => Number.isFinite(valor));
  if (!puntos.length) return <div className="spark" style={{ display: "grid", placeItems: "center", color: "#5c6f65", fontSize: 11 }}>sin datos</div>;
  // Una sola lectura no traza una curva. Decir "sin datos" ahi es falso: el dato
  // existe, y en un nodo recien puesto en marcha es el unico que hay.
  if (puntos.length === 1) {
    return (
      <div className="spark" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, color: "#5c6f65", fontSize: 11 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block" }} />
        <span>Una sola lectura ({puntos[0]}). La curva necesita al menos dos.</span>
      </div>
    );
  }
  const w = 420;
  const min = Math.min(...puntos), max = Math.max(...puntos);
  const span = max - min || 1;
  const pts = puntos.map((v, i) => {
    const x = (i / (puntos.length - 1)) * w;
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
