export function RouteGraphic({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 120 200"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M60 190 C40 170, 80 150, 55 130 C30 110, 75 90, 50 70 C25 50, 70 30, 60 10"
        stroke="#1c1917"
        strokeWidth="3"
        strokeLinecap="round"
        opacity="0.15"
      />
      <path
        d="M60 190 C40 170, 80 150, 55 130 C30 110, 75 90, 50 70 C25 50, 70 30, 60 10"
        stroke="#c8102e"
        strokeWidth="1"
        strokeLinecap="round"
        strokeDasharray="4 6"
        opacity="0.5"
      />
      {[190, 150, 110, 70, 30].map((y, i) => (
        <circle
          key={i}
          cx={i % 2 === 0 ? 58 : 62}
          cy={y}
          r="2.5"
          fill="#c8102e"
          opacity="0.4"
        />
      ))}
    </svg>
  )
}
