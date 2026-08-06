import { useId } from "react";

export default function CircuitBackdrop({ dense = false }: { dense?: boolean }) {
  const uid = useId().replaceAll(":", "");
  const strokeId = `circuitStroke-${uid}`;
  const glowId = `circuitGlow-${uid}`;
  return (
    <div className={`circuit-backdrop ${dense ? "dense" : ""}`} aria-hidden="true">
      <svg viewBox="0 0 1600 900" preserveAspectRatio="none">
        <defs>
          <linearGradient id={strokeId} x1="0" x2="1">
            <stop stopColor="var(--cyan)" stopOpacity="0" />
            <stop offset=".45" stopColor="var(--cyan)" stopOpacity=".5" />
            <stop offset=".72" stopColor="var(--green-bright)" stopOpacity=".65" />
            <stop offset="1" stopColor="var(--green-bright)" stopOpacity="0" />
          </linearGradient>
          <filter id={glowId} x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <g className="circuit-lines" fill="none" stroke={`url(#${strokeId})`} strokeWidth="1.2">
          <path pathLength="1" d="M-80 160H250l55 55h260l80-80h290l75 75h520" />
          <path pathLength="1" d="M40 725h290l80-80h245l74 74h235l105-105h590" />
          <path pathLength="1" d="M115 0v145l70 70v195l-65 65v290" />
          <path pathLength="1" d="M1460-30v205l-80 80v195l90 90v360" />
          <path pathLength="1" d="M520 900V760l55-55V540l-90-90V260l75-75V0" />
          <path pathLength="1" d="M1040 900V730l-72-72V510l90-90V255l-64-64V0" />
          <path pathLength="1" d="M0 430h330l45-45h180l62 62h340l48-48h375l80 80h220" />
        </g>
        <g className="circuit-packets" fill="var(--green-bright)" filter={`url(#${glowId})`}>
          <circle r="3"><animateMotion dur="9s" repeatCount="indefinite" path="M-80 160H250l55 55h260l80-80h290l75 75h520" /></circle>
          <circle r="2.6"><animateMotion dur="11s" begin="-4s" repeatCount="indefinite" path="M40 725h290l80-80h245l74 74h235l105-105h590" /></circle>
          <circle r="2.5" fill="var(--cyan)"><animateMotion dur="12s" begin="-7s" repeatCount="indefinite" path="M0 430h330l45-45h180l62 62h340l48-48h375l80 80h220" /></circle>
        </g>
        <g className="circuit-junctions">
          {[
            [305, 215], [645, 135], [1010, 210], [410, 645], [729, 719], [1069, 614],
            [375, 385], [617, 447], [1005, 399], [1460, 540], [520, 540], [1040, 510],
          ].map(([cx, cy], index) => <circle key={index} cx={cx} cy={cy} r="4" />)}
        </g>
      </svg>
    </div>
  );
}
