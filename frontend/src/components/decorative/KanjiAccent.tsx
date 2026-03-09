interface KanjiAccentProps {
  size?: number
  opacity?: number
  className?: string
}

export function KanjiAccent({ size = 200, opacity = 0.06, className }: KanjiAccentProps) {
  return (
    <span
      className={className}
      style={{
        fontFamily: 'serif',
        fontSize: size,
        lineHeight: 1,
        opacity,
        userSelect: 'none',
        color: '#1c1917',
        letterSpacing: 0,
      }}
      aria-hidden="true"
    >
      峠
    </span>
  )
}
