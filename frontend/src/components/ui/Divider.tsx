import { cn } from '../../lib/utils'

interface DividerProps {
  label?: string
  className?: string
}

export function Divider({ label, className }: DividerProps) {
  if (label) {
    return (
      <div className={cn('flex items-center gap-3 my-3', className)}>
        <div className="flex-1 h-px bg-border" />
        <span className="text-[10px] tracking-widest uppercase text-ink3 font-body">
          {label}
        </span>
        <div className="flex-1 h-px bg-border" />
      </div>
    )
  }
  return <hr className={cn('border-0 border-t border-border my-3', className)} />
}
