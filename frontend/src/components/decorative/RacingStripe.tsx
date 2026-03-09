export function RacingStripe({ className }: { className?: string }) {
  return (
    <div
      className={className}
      style={{
        width: 2,
        background: 'linear-gradient(to bottom, transparent, #c8102e40, transparent)',
        borderRadius: 2,
      }}
      aria-hidden="true"
    />
  )
}
