export function TopoLines({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 800 600"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
        <ellipse
          key={i}
          cx="400"
          cy="300"
          rx={100 + i * 80}
          ry={60 + i * 50}
          fill="none"
          stroke="currentColor"
          strokeWidth="0.8"
          opacity={0.6 - i * 0.07}
        />
      ))}
      {[0, 1, 2, 3].map((i) => (
        <ellipse
          key={`b${i}`}
          cx="650"
          cy="150"
          rx={60 + i * 60}
          ry={40 + i * 40}
          fill="none"
          stroke="currentColor"
          strokeWidth="0.6"
          opacity={0.4 - i * 0.08}
        />
      ))}
      {[0, 1, 2, 3].map((i) => (
        <ellipse
          key={`c${i}`}
          cx="120"
          cy="480"
          rx={50 + i * 55}
          ry={35 + i * 35}
          fill="none"
          stroke="currentColor"
          strokeWidth="0.6"
          opacity={0.4 - i * 0.08}
        />
      ))}
    </svg>
  )
}
