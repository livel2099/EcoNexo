"use client";

import { useState, type CSSProperties } from "react";
import styles from "./LandingLogo.module.css";

const asset = "/brand/econexo-registrada.png";

/** Vista del wordmark original: el archivo de marca no se modifica. */
export function RegisteredWordmark() {
  return <span className={styles.wordmark} role="img" aria-label="EcoNexo, marca registrada">
    <svg viewBox="50 336 405 52" aria-hidden="true" focusable="false">
      <image href={asset} width="500" height="583" />
    </svg>
    <sup aria-hidden="true">®</sup>
  </span>;
}

export default function LandingLogo() {
  const [paused, setPaused] = useState(false);

  return <div className={styles.scene} data-paused={paused}>
    <div className={styles.aura} aria-hidden="true" />
    <div className={styles.artwork} role="img" aria-label="Logo oficial EcoNexo, marca registrada. Análisis predictivo y decisiones en tiempo real.">
      <img className={styles.original} src={asset} width={500} height={583} alt="" fetchPriority="high" />
      <svg className={styles.circuit} viewBox="0 40 500 500" aria-hidden="true" focusable="false">
        <g className={styles.traces} fill="none" strokeLinecap="round" strokeLinejoin="round">
          <path pathLength="1" d="M136 210a114 114 0 1 1 228 0a114 114 0 1 1-228 0" />
          <path pathLength="1" d="M158 242Q177 229 195 234L211 212L240 198L263 163L283 177L305 154L320 138" />
          <path pathLength="1" d="M195 234L219 242L240 198L260 219L283 177" />
          <path pathLength="1" d="M156 260C207 231 212 296 273 274S311 241 350 245" />
          <path pathLength="1" d="M163 273C203 249 220 306 276 284S321 255 343 260" />
          <path pathLength="1" d="M147 186H106L80 160H35M363 209H404L430 182H472M315 302L345 330H400" />
        </g>
        <circle className={styles.orbitalSignal} cx="250" cy="210" r="121" fill="none" pathLength="1" />
        <path className={styles.packet} pathLength="1" fill="none" d="M158 242Q177 229 195 234L211 212L240 198L263 163L283 177L305 154L320 138" />
        <g className={styles.nodes}>{[[147, 186], [195, 234], [211, 212], [240, 198], [263, 163], [283, 177], [305, 154], [320, 138], [363, 209], [315, 302]].map(([cx, cy], index) => <circle key={index} cx={cx} cy={cy} r={index === 7 ? 4 : 2.8} style={{ "--node-index": index } as CSSProperties} />)}</g>
      </svg>
      <div className={styles.scan} aria-hidden="true" />
      <span className={styles.registered} aria-hidden="true">®</span>
    </div>
    <div className={styles.caption}><span><i /> ANÁLISIS · CONEXIÓN · DECISIÓN</span><button type="button" className={styles.motionToggle} onClick={() => setPaused(!paused)} aria-pressed={paused}>{paused ? "Reanudar animación" : "Pausar animación"}</button></div>
  </div>;
}
