import { RARITY_COLORS, TIER_COLORS } from '../../design/tokens'
import { cn, capFirst } from '../../lib/utils'

interface BadgeProps {
  label: string
  type?: 'rarity' | 'tier' | 'default'
  className?: string
}

export function Badge({ label, type = 'default', className }: BadgeProps) {
  const key = label.toLowerCase()
  let color = '#a8a29e'
  if (type === 'rarity' && RARITY_COLORS[key]) color = RARITY_COLORS[key]
  if (type === 'tier' && TIER_COLORS[key]) color = TIER_COLORS[key]

  return (
    <span
      className={cn('inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium tracking-wide uppercase', className)}
      style={{ color, background: `${color}18`, border: `1px solid ${color}30` }}
    >
      {capFirst(label)}
    </span>
  )
}
