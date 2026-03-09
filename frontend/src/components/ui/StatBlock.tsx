import { cn } from '../../lib/utils'

interface StatBlockProps {
  label: string
  value: string | number
  unit?: string
  accent?: boolean
  className?: string
}

export function StatBlock({ label, value, unit, accent, className }: StatBlockProps) {
  return (
    <div className={cn('flex flex-col gap-0.5', className)}>
      <span className="text-[10px] font-medium tracking-widest uppercase text-ink3 font-body">
        {label}
      </span>
      <div className="flex items-baseline gap-1">
        <span
          className="font-display text-display-sm leading-none"
          style={{ color: accent ? '#c47a0a' : '#1c1917' }}
        >
          {value}
        </span>
        {unit && (
          <span className="text-xs text-ink3 font-body">{unit}</span>
        )}
      </div>
    </div>
  )
}
