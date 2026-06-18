// A NASA-evoking circular mission emblem (original artwork, not the NASA logo):
// deep-blue disc, orbit swoosh, star field, and a stylized trajectory.
export default function Emblem({ size = 56 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label="mission emblem">
      <defs>
        <radialGradient id="disc" cx="50%" cy="38%" r="75%">
          <stop offset="0%" stopColor="#1d4ed8" />
          <stop offset="55%" stopColor="#13347f" />
          <stop offset="100%" stopColor="#0a1f4d" />
        </radialGradient>
      </defs>
      <circle cx="50" cy="50" r="48" fill="url(#disc)" stroke="#fc3d21" strokeWidth="2.5" />
      {/* stars */}
      {[
        [22, 28],
        [70, 22],
        [78, 60],
        [33, 70],
        [60, 78],
        [40, 40],
        [64, 45],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r={i % 3 === 0 ? 1.6 : 1} fill="#ffffff" opacity="0.9" />
      ))}
      {/* orbit ellipse */}
      <ellipse
        cx="50"
        cy="52"
        rx="34"
        ry="14"
        fill="none"
        stroke="#50e6ff"
        strokeWidth="2"
        transform="rotate(-24 50 52)"
      />
      {/* trajectory swoosh */}
      <path d="M14 66 Q 50 30 88 44" fill="none" stroke="#fc3d21" strokeWidth="3.4" strokeLinecap="round" />
      {/* craft */}
      <circle cx="88" cy="44" r="3.2" fill="#ffffff" />
    </svg>
  );
}
