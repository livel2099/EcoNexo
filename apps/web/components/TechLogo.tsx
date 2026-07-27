import { useId, type CSSProperties } from "react";

interface TechLogoProps {
  compact?: boolean;
  showTagline?: boolean;
  className?: string;
  light?: boolean;
  label?: string;
}

export default function TechLogo({
  compact = false,
  showTagline = true,
  className = "",
  light = false,
  label = "EcoNexo",
}: TechLogoProps) {
  const classes = ["tech-logo", compact ? "compact" : "", light ? "light" : "", className]
    .filter(Boolean)
    .join(" ");
  const uid = useId().replaceAll(":", "");
  const traceId = `econexoTrace-${uid}`;
  const coreId = `econexoCore-${uid}`;
  const glowId = `econexoGlow-${uid}`;

  return (
    <span className={classes} aria-label={label} role="img">
      <svg className="tech-logo-mark" viewBox="0 0 72 72" aria-hidden="true">
        <defs>
          <linearGradient id={traceId} x1="8" y1="64" x2="64" y2="8" gradientUnits="userSpaceOnUse">
            <stop stopColor="#33daff" />
            <stop offset=".52" stopColor="#8ff06a" />
            <stop offset="1" stopColor="#a78bff" />
          </linearGradient>
          <radialGradient id={coreId} cx="0" cy="0" r="1" gradientTransform="translate(36 36) rotate(90) scale(22)">
            <stop stopColor="#8ff06a" stopOpacity=".26" />
            <stop offset="1" stopColor="#071519" stopOpacity="0" />
          </radialGradient>
          <filter id={glowId} x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="2.8" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        <circle className="tech-logo-field" cx="36" cy="36" r="25.8" fill={`url(#${coreId})`} />
        <path className="tech-logo-orbit orbit-one" d="M12 36a24 24 0 1 0 48 0a24 24 0 1 0-48 0" />
        <path className="tech-logo-orbit orbit-two" d="M20.5 16.5c11.1-8.1 26.8-5.6 34.9 5.5s5.6 26.8-5.5 34.9S23.1 62.5 15 51.4" />

        <g className="tech-logo-traces" fill="none" stroke={`url(#${traceId})`} strokeLinecap="round" strokeLinejoin="round" filter={`url(#${glowId})`}>
          <path className="trace trace-1" pathLength="1" d="M7 18h12l6 6v9" />
          <path className="trace trace-2" pathLength="1" d="M65 18H53l-6 6v7" />
          <path className="trace trace-3" pathLength="1" d="M7 54h12l7-7v-8" />
          <path className="trace trace-4" pathLength="1" d="M65 54H53l-7-7v-8" />
          <path className="trace trace-5" pathLength="1" d="M18 7v10l7 7" />
          <path className="trace trace-6" pathLength="1" d="M54 65V55l-8-8" />
          <path className="trace trace-core" pathLength="1" d="M25 43V29l11-7l11 7v14L36 50Z" />
          <path className="trace trace-leaf" pathLength="1" d="M30 42c1-9 6-14 13-15c0 9-4 15-13 15Zm2-1l9-10" />
        </g>

        <g className="tech-logo-nodes" fill="currentColor">
          <circle className="node node-1" cx="7" cy="18" r="2.2" />
          <circle className="node node-2" cx="65" cy="18" r="2.2" />
          <circle className="node node-3" cx="7" cy="54" r="2.2" />
          <circle className="node node-4" cx="65" cy="54" r="2.2" />
          <circle className="node node-5" cx="18" cy="7" r="2.2" />
          <circle className="node node-6" cx="54" cy="65" r="2.2" />
          <circle className="node core-node" cx="36" cy="36" r="2.7" />
        </g>
        <circle className="tech-logo-packet" cx="0" cy="0" r="2.1" fill="#fff">
          <animateMotion dur="4.8s" repeatCount="indefinite" path="M7 18h12l6 6v9l11 17l11-7V29l6-6h12" />
        </circle>
      </svg>

      <span className="tech-logo-copy">
        <span className="tech-logo-word"><b>ECO</b><strong>NEXO</strong></span>
        {showTagline && <small>{compact ? "EARTH AI" : "EARTH INTELLIGENCE"}</small>}
      </span>
    </span>
  );
}

export function DataPulse({ delay = 0 }: { delay?: number }) {
  return <i className="data-pulse" style={{ "--pulse-delay": `${delay}s` } as CSSProperties} aria-hidden="true" />;
}
