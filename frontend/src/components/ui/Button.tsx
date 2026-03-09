import { cn } from '../../lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md'
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      className={cn(
        'inline-flex items-center justify-center font-body font-medium rounded-btn',
        'transition-all duration-150 active:scale-[0.97]',
        'focus-visible:outline-2 focus-visible:outline-red',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        size === 'md' ? 'px-4 py-2 text-sm' : 'px-3 py-1.5 text-xs',
        variant === 'primary' && 'bg-red text-white hover:bg-red/90',
        variant === 'secondary' &&
          'bg-transparent border border-border-mid text-ink hover:bg-s2',
        variant === 'ghost' && 'bg-transparent text-ink2 hover:text-ink hover:bg-s2',
        className,
      )}
    >
      {children}
    </button>
  )
}
