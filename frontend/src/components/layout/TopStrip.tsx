import { useNavigate } from 'react-router-dom'
import { useStore } from '../../store'
import { UserSummary } from '../../types/api'

interface TopStripProps {
  user?: UserSummary
}

export function TopStrip({ user }: TopStripProps) {
  const clearToken = useStore((s) => s.clearToken)
  const navigate = useNavigate()

  const handleLogout = () => {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <header
      className="flex items-center justify-between px-4 border-b border-border bg-paper"
      style={{ height: 44, flexShrink: 0 }}
    >
      <span className="font-display text-display-xs text-ink tracking-wider">
        TOUGE.DEV
      </span>
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-xs font-body text-ink2">
              <span className="text-ink font-medium">{user.streak}</span> streak
            </span>
            <span className="text-xs font-body text-ink2">
              <span className="text-ink font-medium">{user.gas}</span> gas
            </span>
          </>
        )}
        <button
          onClick={handleLogout}
          className="text-xs font-body text-ink3 hover:text-red transition-colors"
        >
          Exit
        </button>
      </div>
    </header>
  )
}
