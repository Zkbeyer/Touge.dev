import { cn } from '../../lib/utils'

interface PanelProps {
  children: React.ReactNode
  glass?: boolean
  className?: string
}

export function Panel({ children, glass, className }: PanelProps) {
  return (
    <div
      className={cn(
        'rounded-card border',
        glass
          ? 'bg-paper/95 backdrop-blur-xl border-border-mid'
          : 'bg-s1 border-border',
        className,
      )}
    >
      {children}
    </div>
  )
}
