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

        <circle className="tech-logo-field" cx="36" cy="36" r="27" fill={`url(#${coreId})`} />
        <path className="tech-logo-orbit orbit-one" d="M8 36a28 28 0 1 0 56 0a28 28 0 1 0-56 0" />
        <path className="tech-logo-orbit orbit-two" d="M17 13.5C29 4.8 46 7.4 54.7 19.3S60.8 48.4 49 57S19.9 63.2 11.2 51.3" />
        <circle className="tech-logo-globe" cx="36" cy="36" r="22.3" />

        <g className="tech-logo-traces" fill="none" stroke={`url(#${traceId})`} strokeLinecap="round" strokeLinejoin="round" filter={`url(#${glowId})`}>
          <path className="trace trace-1" pathLength="1" d="M17 39l7-6l7 3l8-12l7 6l9-11" />
          <path className="trace trace-2" pathLength="1" d="M13 48c8-7 14 2 23-2s13-11 23-7" />
          <path className="trace trace-3" pathLength="1" d="M13 51c9-6 15 4 24 0s13-10 22-7" />
          <path className="trace trace-4" pathLength="1" d="M15 54c9-4 14 4 23 1s12-8 20-6" />
          <path className="trace trace-5" pathLength="1" d="M11 23h7l4 4" />
          <path className="trace trace-6" pathLength="1" d="M61 31h-5l-3 3" />
        </g>

        <g className="tech-logo-nodes" fill="currentColor">
          <circle className="node node-1" cx="17" cy="39" r="1.8" />
          <circle className="node node-2" cx="24" cy="33" r="1.8" />
          <circle className="node node-3" cx="31" cy="36" r="1.8" />
          <circle className="node node-4" cx="39" cy="24" r="1.8" />
          <circle className="node node-5" cx="46" cy="30" r="1.8" />
          <circle className="node node-6" cx="55" cy="19" r="1.8" />
        </g>
        <g className="tech-logo-pixels" fill="currentColor" aria-hidden="true">
          <circle cx="23" cy="20" r=".75"/><circle cx="27" cy="18.5" r=".85"/><circle cx="31" cy="18" r=".9"/><circle cx="35" cy="18.5" r=".75"/>
          <circle cx="21.5" cy="23.5" r=".7"/><circle cx="26" cy="22.5" r=".8"/><circle cx="30" cy="22" r=".75"/><circle cx="34" cy="22.5" r=".65"/>
          <circle cx="21" cy="27" r=".65"/><circle cx="25" cy="26" r=".75"/><circle cx="29" cy="26" r=".6"/>
        </g>
        <circle className="tech-logo-packet" cx="0" cy="0" r="2.1" fill="#fff">
          <animateMotion dur="4.8s" repeatCount="indefinite" path="M17 39l7-6l7 3l8-12l7 6l9-11" />
        </circle>
      </svg>

      <span className="tech-logo-copy">
        <span className="tech-logo-word"><b>ECO</b><strong>NEXO</strong></span>
        {showTagline && <small>{compact ? "EARTH AI" : "EARTH INTELLIGENCE"}</small>}
      </span>
    </span>
  );
}

export function OfficialLogoMotion({ className = "" }: { className?: string }) {
  return (
    <div className={`official-logo-motion ${className}`.trim()} role="img" aria-label="EcoNexo · análisis predictivo y decisiones en tiempo real">
      <img src="/brand/econexo-oficial-login.jpg" alt="" />
      <svg viewBox="0 0 320 180" preserveAspectRatio="none" aria-hidden="true">
        <g className="official-logo-ai-lines" fill="none" strokeLinecap="round" strokeLinejoin="round">
          <path pathLength="1" d="M-18 43h55l18 16h43l19-21h54l18 17h58l22-20h70" />
          <path pathLength="1" d="M-10 142h47l24-22h50l21 18h55l22-25h54l21 16h48" />
          <path pathLength="1" d="M26 182v-25l22-20v-31l-17-16V52" />
          <path pathLength="1" d="M286-8v31l-19 18v30l17 16v42" />
        </g>
        <g className="official-logo-ai-nodes">
          <circle cx="55" cy="59" r="3"/><circle cx="117" cy="38" r="2.5"/><circle cx="189" cy="55" r="3"/><circle cx="269" cy="35" r="2.5"/>
          <circle cx="61" cy="120" r="2.5"/><circle cx="132" cy="138" r="3"/><circle cx="209" cy="113" r="2.5"/><circle cx="284" cy="129" r="3"/>
        </g>
        <circle className="official-logo-packet" r="3">
          <animateMotion dur="5.8s" repeatCount="indefinite" path="M-18 43h55l18 16h43l19-21h54l18 17h58l22-20h70" />
        </circle>
        <circle className="official-logo-packet packet-two" r="2.6">
          <animateMotion dur="7.4s" begin="-3s" repeatCount="indefinite" path="M-10 142h47l24-22h50l21 18h55l22-25h54l21 16h48" />
        </circle>
      </svg>
    </div>
  );
}

export function DataPulse({ delay = 0 }: { delay?: number }) {
  return <i className="data-pulse" style={{ "--pulse-delay": `${delay}s` } as CSSProperties} aria-hidden="true" />;
}
